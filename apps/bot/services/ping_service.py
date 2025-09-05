"""
Сервис для системы пингов пользователей
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List, Dict, Optional
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from shared.models.user import User
from shared.models.conversation import Conversation, Message
from shared.models.analytics import Event
from .settings_service import SettingsService
from utils.ux_helper import UXHelper
import pytz
import logging

logger = logging.getLogger(__name__)


class PingService:
    """Сервис управления пингами пользователей"""
    
    def __init__(self):
        pass
    
    async def should_send_ping(self, user: User, settings: Dict) -> Dict:
        """
        Определяет, нужно ли отправить пинг пользователю
        
        Args:
            user: Пользователь
            settings: Настройки пингов
            
        Returns:
            Dict с информацией о типе пинга или None
        """
        # Проверяем, включены ли пинги у пользователя
        if not user.ping_enabled:
            return None
            
        # Проверяем, не в кризисном режиме ли пользователь
        if user.is_in_crisis:
            return None
            
        # Получаем настройки из админки
        ping_enabled = settings.get('ping_enabled', True)
        if not ping_enabled:
            return None
            
        # Проверяем разрешенные часы для пингов
        if not await self._is_allowed_ping_time(user, settings):
            return None
            
        now = datetime.utcnow()
        # Use new progressive delay settings, fallback to legacy idle_ping_delay
        progressive_ping_1_delay = settings.get('progressive_ping_1_delay', settings.get('idle_ping_delay', 30))
        
        async with async_session() as session:
            # Ищем последнее сообщение пользователя
            last_message = await session.execute(
                select(Message)
                .join(Conversation)
                .where(
                    and_(
                        Conversation.user_id == user.id,
                        Message.role == 'user'
                    )
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            last_message_obj = last_message.scalar_one_or_none()
            
            if not last_message_obj:
                return None
                
            time_since_last = now - last_message_obj.created_at
            
            # Проверяем последний отправленный пинг
            last_ping_event = await session.execute(
                select(Event)
                .where(
                    and_(
                        Event.user_id == user.id,
                        Event.event_type == 'ping_sent'
                    )
                )
                .order_by(Event.created_at.desc())
                .limit(1)
            )
            last_ping = last_ping_event.scalar_one_or_none()
            
            # Прогрессивная система пингов
            return await self._calculate_progressive_ping(
                user.id, 
                last_message_obj.created_at, 
                last_ping, 
                now, 
                session,
                settings
            )
        
        return None

    async def _calculate_progressive_ping(
        self, 
        user_id: int, 
        last_message_time: datetime, 
        last_ping_event, 
        now: datetime,
        session: AsyncSession,
        settings: Dict
    ) -> Dict:
        """
        Прогрессивная система пингов с настраиваемыми интервалами:
        1. Через progressive_ping_1_delay минут после последнего сообщения
        2. Через progressive_ping_2_delay минут после первого пинга  
        3. Через progressive_ping_3_delay минут после второго пинга
        """
        time_since_last_message = now - last_message_time
        
        # Получаем настройки задержек (в минутах)
        ping_1_delay = settings.get('progressive_ping_1_delay', settings.get('idle_ping_delay', 30))
        ping_2_delay = settings.get('progressive_ping_2_delay', 120)  # 2 часа
        ping_3_delay = settings.get('progressive_ping_3_delay', 1440)  # 24 часа
        
        # Считаем количество пингов после последнего сообщения пользователя
        pings_after_last_message = await session.execute(
            select(func.count(Event.id))
            .where(
                and_(
                    Event.user_id == user_id,
                    Event.event_type == 'ping_sent',
                    Event.created_at > last_message_time
                )
            )
        )
        ping_count = pings_after_last_message.scalar() or 0
        
        # 1-й пинг: через настраиваемое время после последнего сообщения
        if ping_count == 0 and time_since_last_message >= timedelta(minutes=ping_1_delay):
            return {
                'type': 'progressive_ping_1',
                'level': 1,
                'last_activity': last_message_time
            }
        
        # 2-й пинг: через настраиваемое время после первого пинга
        if ping_count == 1 and last_ping_event:
            time_since_first_ping = now - last_ping_event.created_at
            if time_since_first_ping >= timedelta(minutes=ping_2_delay):
                return {
                    'type': 'progressive_ping_2', 
                    'level': 2,
                    'last_activity': last_message_time
                }
        
        # 3-й пинг: через настраиваемое время после второго пинга
        if ping_count == 2 and last_ping_event:
            time_since_second_ping = now - last_ping_event.created_at
            if time_since_second_ping >= timedelta(minutes=ping_3_delay):
                return {
                    'type': 'progressive_ping_3',
                    'level': 3, 
                    'last_activity': last_message_time
                }
        
        # После 3-го пинга больше не отправляем (или можно добавить логику повтора через неделю)
        return None
    
    async def check_session_timeout(self, user: User, settings: Dict) -> bool:
        """
        Проверяет и закрывает сессии по таймауту
        
        Returns:
            True если сессия была закрыта
        """
        session_close_timeout = settings.get('session_close_timeout', 48)
        now = datetime.utcnow()
        timeout_threshold = now - timedelta(hours=session_close_timeout)
        
        async with async_session() as session:
            # Ищем активные сессии пользователя
            active_conversations = await session.execute(
                select(Conversation)
                .where(
                    and_(
                        Conversation.user_id == user.id,
                        Conversation.is_active == True
                    )
                )
                .order_by(Conversation.created_at.desc())
            )
            active_convs = active_conversations.scalars().all()
            
            sessions_closed = False
            
            for conv in active_convs:
                # Ищем последнее сообщение в сессии
                last_message = await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
                last_msg = last_message.scalar_one_or_none()
                
                # Если последнее сообщение старше timeout_threshold, закрываем сессию
                if last_msg and last_msg.created_at < timeout_threshold:
                    from services.conversation_service import ConversationService
                    conv_service = ConversationService(session)
                    await conv_service.close_conversation(conv)
                    sessions_closed = True
                    
                    logger.info(f"Closed session {conv.id} for user {user.id} due to timeout")
            
            return sessions_closed
    
    async def _is_allowed_ping_time(self, user: User, settings: Dict) -> bool:
        """
        Проверяет, входит ли текущее время в разрешенные часы для пингов
        с учетом часового пояса пользователя
        """
        # Получаем настройки часов пингов
        allowed_start = settings.get('allowed_ping_hours_start', 10)  # 10:00
        allowed_end = settings.get('allowed_ping_hours_end', 21)      # 21:00
        
        # Определяем текущее время в часовом поясе пользователя
        current_hour = self._get_user_current_hour(user)
        
        # Проверяем, входит ли час в разрешенный диапазон
        if allowed_start <= allowed_end:
            # Обычный случай: 10:00 - 21:00
            return allowed_start <= current_hour <= allowed_end
        else:
            # Переход через полночь: 22:00 - 8:00
            return current_hour >= allowed_start or current_hour <= allowed_end
    
    def _get_user_current_hour(self, user: User) -> int:
        """Получает текущий час в часовом поясе пользователя"""
        try:
            if user.timezone:
                tz = pytz.timezone(user.timezone)
                user_time = datetime.now(tz)
                return user_time.hour
        except Exception as e:
            logger.warning(f"Failed to get user timezone {user.timezone}: {e}")
        
        # Fallback to UTC
        return datetime.utcnow().hour
    
    async def get_ping_text(self, user: User, settings: Dict, ping_type: str = 'progressive_ping_1') -> str:
        """
        Генерирует текст пинга для пользователя
        
        Args:
            user: Пользователь
            settings: Настройки
            ping_type: Тип пинга ('progressive_ping_1', 'progressive_ping_2', 'progressive_ping_3', 'idle_ping')
            
        Returns:
            Текст пинга
        """
        # Проверяем, включена ли AI-генерация
        ai_generation_enabled = settings.get('ping_ai_generation_enabled', False)
        
        if ai_generation_enabled:
            try:
                return await self._generate_ai_ping_text(user, settings, ping_type)
            except Exception as e:
                logger.warning(f"AI ping generation failed for user {user.id}: {e}, falling back to templates")
        
        # Используем шаблоны если AI отключен или недоступен
        return await self._get_template_ping_text(user, settings, ping_type)
    
    async def _generate_ai_ping_text(self, user: User, settings: Dict, ping_type: str) -> str:
        """Генерирует текст пинга с помощью AI"""
        from .ping_ai_service import PingAIService
        
        # Получаем системный промпт и уровень пинга
        system_prompt = settings.get('ping_ai_system_prompt', 
            "Создай короткое теплое сообщение для проверки связи с пользователем.")
        
        ping_level = int(ping_type.split('_')[-1]) if ping_type.startswith('progressive_ping_') else 1
        
        # Формируем контекст о последней активности пользователя
        user_context = {}
        
        ping_ai_service = PingAIService()
        return await ping_ai_service.generate_ping_text(
            user=user,
            ping_level=ping_level,
            system_prompt=system_prompt,
            user_context=user_context
        )
    
    async def _get_template_ping_text(self, user: User, settings: Dict, ping_type: str) -> str:
        """Получает текст пинга из шаблонов (legacy метод)"""
        # Прогрессивные пинги с разной интенсивностью
        if ping_type == 'progressive_ping_1':
            # Первый пинг - мягкий
            ping_templates = settings.get('progressive_ping_1_templates', [
                "Ты ещё здесь? Я на связи 💙",
                "Как дела, {name}? Я слушаю 🤗", 
                "Всё в порядке? 💭",
                "Если нужно поговорить, я здесь ✨"
            ])
        elif ping_type == 'progressive_ping_2':
            # Второй пинг - более заинтересованный
            ping_templates = settings.get('progressive_ping_2_templates', [
                "👋 {name}, думаю о тебе. Как настроение?",
                "🌟 Хочется узнать, как ты себя чувствуешь?", 
                "💭 {name}, поделишься, что у тебя на душе?",
                "🤗 Как прошло время? Расскажешь?"
            ])
        elif ping_type == 'progressive_ping_3':
            # Третий пинг - более настойчивый, заботливый
            ping_templates = settings.get('progressive_ping_3_templates', [
                "🌈 {name}, я беспокоюсь. Как ты?",
                "💙 Давно не слышал от тебя. Всё ли хорошо?", 
                "☀️ {name}, надеюсь, у тебя все в порядке. Я здесь, если нужно поговорить",
                "🫂 Скучаю по нашим разговорам. Как дела?"
            ])
        elif ping_type == 'idle_ping':
            # Старый формат для совместимости
            ping_templates = settings.get('idle_ping_templates', [
                "Ты ещё здесь? Я на связи 💙",
                "Как дела? Я слушаю 🤗", 
                "Всё в порядке? 💭"
            ])
        else:  # daily_ping и остальные
            ping_templates = settings.get('ping_templates', [
                "👋 Привет, {name}! Как дела? Что у тебя на душе?",
                "🌟 {day_part}, {name}! Думаю о тебе. Как настроение?", 
                "💭 Хочется узнать, как ты, {name}? Поделишься?",
                "🌈 Надеюсь, у тебя все хорошо, {name}. Расскажешь, как дела?",
                "☀️ {day_part}! Как ты себя чувствуешь, {name}?"
            ])
        
        if not ping_templates:
            return "👋 Привет! Как дела?"
        
        # Выбираем случайный шаблон
        import random
        template = random.choice(ping_templates)
        
        # Заменяем переменные
        template = self._substitute_variables(template, user)
            
        return template
    
    def _substitute_variables(self, template: str, user: User) -> str:
        """Заменяет переменные в шаблоне пинга"""
        import pytz
        from datetime import datetime
        
        # Подстановка имени
        if '{name}' in template:
            name = user.name if user.name else "друг мой"
            template = template.replace('{name}', name)
        
        # Подстановка времени суток
        if '{day_part}' in template:
            try:
                if user.timezone:
                    tz = pytz.timezone(user.timezone)
                    current_hour = datetime.now(tz).hour
                else:
                    current_hour = datetime.utcnow().hour
                    
                if 5 <= current_hour < 12:
                    day_part = "Доброе утро"
                elif 12 <= current_hour < 17:
                    day_part = "Добрый день" 
                elif 17 <= current_hour < 22:
                    day_part = "Добрый вечер"
                else:
                    day_part = "Доброй ночи"
                    
                template = template.replace('{day_part}', day_part)
            except Exception:
                template = template.replace('{day_part}', "Привет")
        
        return template
    
    async def send_ping(self, user_id: int, bot_instance) -> bool:
        """
        Отправляет пинг конкретному пользователю
        
        Args:
            user_id: ID пользователя
            bot_instance: Экземпляр бота для отправки сообщений
            
        Returns:
            True если пинг отправлен успешно
        """
        try:
            async with async_session() as session:
                settings_service = SettingsService(session)
                
                # Получаем пользователя
                user_result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    return False
                
                # Получаем настройки пингов
                settings = {
                    'ping_enabled': await settings_service.get_setting('ping_enabled', True),
                    'allowed_ping_hours_start': await settings_service.get_setting('allowed_ping_hours_start', 10),
                    'allowed_ping_hours_end': await settings_service.get_setting('allowed_ping_hours_end', 21),
                    'session_close_timeout': await settings_service.get_setting('session_close_timeout', 48),
                    
                    # Progressive ping timing settings
                    'progressive_ping_1_delay': await settings_service.get_setting('progressive_ping_1_delay', 30),
                    'progressive_ping_2_delay': await settings_service.get_setting('progressive_ping_2_delay', 120),
                    'progressive_ping_3_delay': await settings_service.get_setting('progressive_ping_3_delay', 1440),
                    
                    # AI settings
                    'ping_ai_generation_enabled': await settings_service.get_setting('ping_ai_generation_enabled', False),
                    'ping_ai_system_prompt': await settings_service.get_setting('ping_ai_system_prompt', "Создай короткое теплое сообщение для проверки связи с пользователем."),
                    
                    # Template settings
                    'progressive_ping_1_templates': await settings_service.get_setting('progressive_ping_1_templates', []),
                    'progressive_ping_2_templates': await settings_service.get_setting('progressive_ping_2_templates', []),
                    'progressive_ping_3_templates': await settings_service.get_setting('progressive_ping_3_templates', [])
                }
                
                # Проверяем, нужно ли отправлять пинг
                ping_info = await self.should_send_ping(user, settings)
                if not ping_info:
                    return False
                
                # Проверяем и закрываем сессии по таймауту
                await self.check_session_timeout(user, settings)
                
                # Генерируем текст пинга
                ping_text = await self.get_ping_text(user, settings, ping_info['type'])
                
                # Отправляем пинг
                await bot_instance.send_message(
                    chat_id=user.telegram_id,
                    text=ping_text
                )
                
                # Логируем отправку пинга
                ping_event = Event(
                    user_id=user.id,
                    event_type='ping_sent',
                    properties={'ping_text': ping_text}
                )
                session.add(ping_event)
                await session.commit()
                
                logger.info(f"Ping sent to user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send ping to user {user_id}: {e}")
            return False
    
    async def schedule_ping_check(self, bot_instance):
        """
        Планирует проверку пингов для всех пользователей
        Запускается периодически (например, каждые 30 минут)
        """
        try:
            async with async_session() as session:
                settings_service = SettingsService(session)
                
                # Получаем общие настройки пингов
                ping_enabled = await settings_service.get_setting('ping_enabled', True)
                if not ping_enabled:
                    return
                
                # Получаем всех активных пользователей с включенными пингами
                users_result = await session.execute(
                    select(User).where(
                        and_(
                            User.is_active == True,
                            User.ping_enabled == True,
                            User.is_in_crisis == False,
                            User.terms_accepted == True
                        )
                    )
                )
                users = users_result.scalars().all()
                
                settings = {
                    'ping_enabled': ping_enabled,
                    'allowed_ping_hours_start': await settings_service.get_setting('allowed_ping_hours_start', 10),
                    'allowed_ping_hours_end': await settings_service.get_setting('allowed_ping_hours_end', 21),
                    'session_close_timeout': await settings_service.get_setting('session_close_timeout', 48),
                    
                    # Progressive ping timing settings
                    'progressive_ping_1_delay': await settings_service.get_setting('progressive_ping_1_delay', 30),
                    'progressive_ping_2_delay': await settings_service.get_setting('progressive_ping_2_delay', 120),
                    'progressive_ping_3_delay': await settings_service.get_setting('progressive_ping_3_delay', 1440),
                    
                    # AI settings
                    'ping_ai_generation_enabled': await settings_service.get_setting('ping_ai_generation_enabled', False),
                    'ping_ai_system_prompt': await settings_service.get_setting('ping_ai_system_prompt', "Создай короткое теплое сообщение для проверки связи с пользователем."),
                    
                    # Template settings
                    'progressive_ping_1_templates': await settings_service.get_setting('progressive_ping_1_templates', []),
                    'progressive_ping_2_templates': await settings_service.get_setting('progressive_ping_2_templates', []),
                    'progressive_ping_3_templates': await settings_service.get_setting('progressive_ping_3_templates', []),
                    
                    # Legacy settings for backward compatibility
                    'idle_ping_delay': await settings_service.get_setting('idle_ping_delay', 30)
                }
                
                ping_count = 0
                for user in users:
                    if await self.should_send_ping(user, settings):
                        success = await self.send_ping(user.id, bot_instance)
                        if success:
                            ping_count += 1
                        
                        # Небольшая задержка между пингами чтобы не заспамить
                        await asyncio.sleep(0.5)
                
                logger.info(f"Ping check completed. Sent {ping_count} pings to {len(users)} users")
                
        except Exception as e:
            logger.error(f"Failed to run ping check: {e}")
    
    async def get_ping_stats(self) -> Dict:
        """Получает статистику по пингам"""
        try:
            async with async_session() as session:
                now = datetime.utcnow()
                today = now.replace(hour=0, minute=0, second=0, microsecond=0)
                week_ago = today - timedelta(days=7)
                
                # Пинги сегодня
                pings_today = await session.execute(
                    select(func.count(Event.id))
                    .where(
                        and_(
                            Event.event_type == 'ping_sent',
                            Event.created_at >= today
                        )
                    )
                )
                
                # Пинги за неделю
                pings_week = await session.execute(
                    select(func.count(Event.id))
                    .where(
                        and_(
                            Event.event_type == 'ping_sent',
                            Event.created_at >= week_ago
                        )
                    )
                )
                
                # Пользователи с включенными пингами
                enabled_users = await session.execute(
                    select(func.count(User.id))
                    .where(User.ping_enabled == True)
                )
                
                return {
                    'pings_sent_today': pings_today.scalar(),
                    'pings_sent_week': pings_week.scalar(),
                    'users_with_pings_enabled': enabled_users.scalar()
                }
                
        except Exception as e:
            logger.error(f"Failed to get ping stats: {e}")
            return {
                'pings_sent_today': 0,
                'pings_sent_week': 0,
                'users_with_pings_enabled': 0
            }
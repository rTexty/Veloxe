"""
AI-сервис для генерации текстов пингов
"""
import asyncio
from openai import AsyncOpenAI
from typing import Dict, Optional
import sys
sys.path.append('../../../')

from shared.config.settings import settings
from shared.models.user import User
import logging

logger = logging.getLogger(__name__)


class PingAIService:
    """Сервис для AI-генерации текстов пингов"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def generate_ping_text(
        self, 
        user: User, 
        ping_level: int, 
        system_prompt: str,
        user_context: Optional[Dict] = None
    ) -> str:
        """
        Генерирует текст пинга с помощью AI
        
        Args:
            user: Пользователь для которого генерируется пинг
            ping_level: Уровень пинга (1, 2, 3)
            system_prompt: Системный промпт для генерации
            user_context: Дополнительный контекст о пользователе
            
        Returns:
            Сгенерированный текст пинга
        """
        try:
            # Формируем промпт с учетом уровня и пользователя
            level_instructions = self._get_level_instructions(ping_level)
            user_info = self._format_user_info(user, user_context)
            
            # Формируем сообщения для GPT
            messages = [
                {
                    "role": "system", 
                    "content": f"{system_prompt}\n\n{level_instructions}"
                },
                {
                    "role": "user",
                    "content": f"Создай сообщение для пинга {ping_level} уровня.\n\n{user_info}\n\nСообщение должно быть коротким (до 50 символов), теплым и подходящим для данного уровня контакта."
                }
            ]
            
            # Вызываем OpenAI API
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=50,
                temperature=0.8,
                timeout=10.0
            )
            
            generated_text = response.choices[0].message.content.strip()
            
            # Подставляем переменные пользователя
            generated_text = self._substitute_user_variables(generated_text, user)
            
            logger.info(f"Generated ping level {ping_level} for user {user.id}: {generated_text}")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Failed to generate AI ping for user {user.id}, level {ping_level}: {e}")
            # Возвращаем fallback сообщение
            return self._get_fallback_ping(ping_level, user)
    
    def _get_level_instructions(self, ping_level: int) -> str:
        """Получает инструкции для конкретного уровня пинга"""
        instructions = {
            1: "Уровень 1 - Мягкий контакт: Создай очень деликатное, ненавязчивое сообщение. Тон должен быть дружелюбным но не настойчивым.",
            2: "Уровень 2 - Заинтересованность: Покажи больше заинтересованности и заботы. Можно быть немного более прямым в выражении желания поговорить.",
            3: "Уровень 3 - Забота и беспокойство: Выражай искреннюю заботу и легкое беспокойство. Покажи, что пользователь важен и его отсутствие замечено."
        }
        return instructions.get(ping_level, instructions[1])
    
    def _format_user_info(self, user: User, context: Optional[Dict] = None) -> str:
        """Форматирует информацию о пользователе для контекста"""
        info_parts = []
        
        if user.name:
            info_parts.append(f"Имя пользователя: {user.name}")
        
        if user.age:
            info_parts.append(f"Возраст: {user.age}")
        
        if user.gender:
            gender_map = {"male": "мужской", "female": "женский", "not_applicable": "не указан"}
            info_parts.append(f"Пол: {gender_map.get(user.gender, user.gender)}")
        
        if user.emotion_tags:
            emotions = ", ".join(user.emotion_tags[:3])  # Первые 3 эмоции
            info_parts.append(f"Основные эмоции: {emotions}")
        
        if context:
            if context.get('last_activity_hours'):
                info_parts.append(f"Последняя активность: {context['last_activity_hours']} часов назад")
        
        return "\n".join(info_parts) if info_parts else "Информация о пользователе не доступна"
    
    def _substitute_user_variables(self, text: str, user: User) -> str:
        """Подставляет переменные пользователя в сгенерированный текст"""
        import pytz
        from datetime import datetime
        
        # Подстановка имени
        if '{name}' in text:
            name = user.name if user.name else "друг мой"
            text = text.replace('{name}', name)
        
        # Подстановка времени суток
        if '{day_part}' in text:
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
                    
                text = text.replace('{day_part}', day_part)
            except Exception:
                text = text.replace('{day_part}', "Привет")
        
        return text
    
    def _get_fallback_ping(self, ping_level: int, user: User) -> str:
        """Возвращает fallback сообщение при ошибке AI-генерации"""
        fallback_messages = {
            1: [
                "Ты ещё здесь? Я на связи 💙",
                "Как дела? Я слушаю 🤗", 
                "Всё в порядке? 💭"
            ],
            2: [
                "👋 Думаю о тебе. Как настроение?",
                "🌟 Хочется узнать, как ты себя чувствуешь?", 
                "💭 Поделишься, что у тебя на душе?"
            ],
            3: [
                "🌈 Я беспокоюсь. Как ты?",
                "💙 Давно не слышал от тебя. Всё ли хорошо?", 
                "☀️ Надеюсь, у тебя все в порядке. Я здесь 🤗"
            ]
        }
        
        import random
        messages = fallback_messages.get(ping_level, fallback_messages[1])
        template = random.choice(messages)
        
        # Подставляем имя пользователя если есть placeholder
        if '{name}' in template and user.name:
            template = template.replace('{name}', user.name)
        elif '{name}' in template:
            template = template.replace('{name}', "друг мой")
            
        return template
    
    async def test_generation(self, system_prompt: str, test_level: int = 1) -> str:
        """
        Тестирует генерацию пинга для предпросмотра в админке
        
        Args:
            system_prompt: Системный промпт для тестирования
            test_level: Уровень пинга для тестирования
            
        Returns:
            Сгенерированный тестовый пинг
        """
        try:
            level_instructions = self._get_level_instructions(test_level)
            
            messages = [
                {
                    "role": "system", 
                    "content": f"{system_prompt}\n\n{level_instructions}"
                },
                {
                    "role": "user",
                    "content": f"Создай тестовое сообщение для пинга {test_level} уровня. Имя пользователя: Анна, возраст: 25, пол: женский. Сообщение должно быть коротким (до 50 символов), теплым и подходящим для данного уровня."
                }
            ]
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=50,
                temperature=0.8,
                timeout=10.0
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate test ping: {e}")
            return f"Ошибка тестирования: {str(e)}"
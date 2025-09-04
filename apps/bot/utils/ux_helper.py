import asyncio
from typing import Optional, List, Union
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import logging

logger = logging.getLogger(__name__)


class UXHelper:
    """Утилиты для красивого и плавного UX в боте"""
    
    @staticmethod
    async def typing_action(chat_id: int, bot, duration: float = 0.2):
        """Показать индикатор печати"""
        try:
            await bot.send_chat_action(chat_id, "typing")
            await asyncio.sleep(duration)
        except Exception as e:
            logger.error(f"Failed to send typing action: {e}")
    
    @staticmethod
    async def smooth_edit_text(
        message: types.Message,
        new_text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        typing_delay: float = 0.3,
        parse_mode: Optional[str] = "HTML"
    ):
        """Плавно редактировать сообщение с индикатором печати"""
        try:
            # Показать индикатор печати
            await UXHelper.typing_action(message.chat.id, message.bot, typing_delay)
            
            # Редактировать сообщение
            await message.edit_text(
                new_text, 
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.error(f"Failed to edit message: {e}")
                # Если не можем редактировать, отправляем новое
                await message.answer(new_text, reply_markup=reply_markup, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Error in smooth_edit_text: {e}")
    
    @staticmethod
    async def smooth_answer(
        message: types.Message,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        typing_delay: float = 0.3,
        parse_mode: Optional[str] = "HTML"
    ):
        """Отправить сообщение с индикатором печати"""
        try:
            # Показать индикатор печати
            await UXHelper.typing_action(message.chat.id, message.bot, typing_delay)
            
            # Отправить сообщение
            return await message.answer(
                text, 
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Error in smooth_answer: {e}")
            return None
    
    @staticmethod
    async def smooth_send_message(
        bot,
        chat_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        typing_delay: float = 1.2,
        parse_mode: Optional[str] = "HTML"
    ):
        """Отправить сообщение в чат с индикатором печати"""
        try:
            # Показать индикатор печати
            await UXHelper.typing_action(chat_id, bot, typing_delay)
            
            # Отправить сообщение
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Error in smooth_send_message: {e}")
            return None
    
    @staticmethod
    async def progress_edit(
        message: types.Message,
        steps: List[str],
        final_text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        step_delay: float = 1.0
    ):
        """Показать прогресс через редактирование сообщения"""
        try:
            for i, step in enumerate(steps):
                # Показать текущий шаг
                progress_bar = "▓" * (i + 1) + "░" * (len(steps) - i - 1)
                step_text = f"{step}\n\n{progress_bar}"
                
                await UXHelper.smooth_edit_text(
                    message, 
                    step_text, 
                    typing_delay=step_delay * 0.6
                )
                
                await asyncio.sleep(step_delay)
            
            # Показать финальный текст
            await UXHelper.smooth_edit_text(
                message, 
                final_text, 
                reply_markup=reply_markup,
                typing_delay=0.5
            )
            
        except Exception as e:
            logger.error(f"Error in progress_edit: {e}")
            # Fallback к обычному сообщению
            await message.answer(final_text, reply_markup=reply_markup)


class OnboardingUX:
    """Специализированные утилиты для онбординга"""
    
    @staticmethod
    def create_button_keyboard(buttons: List[tuple], rows: int = 1) -> InlineKeyboardMarkup:
        """Создать красивую клавиатуру из кнопок"""
        keyboard = []
        buttons_per_row = len(buttons) // rows if len(buttons) % rows == 0 else len(buttons) // rows + 1
        
        for i in range(0, len(buttons), buttons_per_row):
            row = []
            for j in range(buttons_per_row):
                if i + j < len(buttons):
                    text, callback_data = buttons[i + j]
                    row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
            keyboard.append(row)
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    @staticmethod
    async def animated_welcome(
        message: types.Message,
        user_name: str = "друг",
        user_profile: dict = None
    ):
        """Анимированное приветствие с генерируемым GPT текстом"""
        from services.greeting_service import GreetingService
        from services.settings_service import SettingsService
        from shared.config.database import async_session
        
        # Check if dynamic greetings are enabled
        async with async_session() as session:
            settings_service = SettingsService(session)
            greeting_enabled = await settings_service.get_setting("greeting_enabled", True)
            
            if greeting_enabled:
                try:
                    # Generate personalized greeting
                    greeting_service = GreetingService()
                    custom_greeting = await greeting_service.generate_greeting(
                        user_profile or {"name": user_name},
                        scenario="first_time"
                    )
                    
                    # Use generated greeting as first step
                    welcome_steps = [
                        custom_greeting,
                        f"🌟 Добро пожаловать в безопасное пространство",
                        # f"🛡️ Всё конфиденциально и анонимно"  # ВРЕМЕННО ОТКЛЮЧЕНО
                    ]
                except Exception as e:
                    print(f"Failed to generate greeting: {e}")
                    # Fallback to static greeting
                    welcome_steps = [
                        f"👋 Привет, {user_name}!",
                        f"🌟 Добро пожаловать в безопасное пространство",
                        # f"🛡️ Всё конфиденциально и анонимно"  # ВРЕМЕННО ОТКЛЮЧЕНО
                    ]
            else:
                # Static greeting when disabled
                welcome_steps = [
                    f"👋 Привет, {user_name}!",
                    f"🌟 Добро пожаловать в безопасное пространство",
                    # f"🛡️ Всё конфиденциально и анонимно"  # ВРЕМЕННО ОТКЛЮЧЕНО
                ]
        
        final_text = f"""🌸 <b>Добро пожаловать, {user_name}!</b>

Ты в безопасном пространстве для души. Здесь можно:
• 💬 Поделиться переживаниями  
• 🧘‍♀️ Найти покой и поддержку
• 📈 Отследить своё эмоциональное состояние

⚠️ <i>Это не замена психотерапии. В кризисных ситуациях звони 112.</i>"""
        
        keyboard = OnboardingUX.create_button_keyboard([
            ("✅ Я согласен продолжить", "consent_accept"),
            ("📋 Условия использования", "show_full_policy"),
            ("❌ Не готов", "consent_decline")
        ], rows=2)
        
        # ВРЕМЕННО ОТКЛЮЧЕНА АНИМАЦИЯ ЗАГРУЗКИ
        # await UXHelper.progress_edit(
        #     message,
        #     welcome_steps,
        #     final_text,
        #     keyboard,
        #     step_delay=1.2
        # )
        
        # Показываем сразу финальный текст без анимации
        await UXHelper.smooth_edit_text(
            message,
            final_text,
            keyboard,
            typing_delay=0.8
        )
    
    @staticmethod
    async def survey_intro_animation(message: types.Message):
        """Анимированное начало анкеты"""
        
        final_text = """🌟 <b>Давайте познакомимся поближе!</b>

Несколько простых вопросов помогут мне:
• 💡 Лучше понимать ваши потребности
• 💡 Давать более персонализированные советы  
• 🌈 Создать комфортную атмосферу для общения

<i>Все данные конфиденциальны и используются только для улучшения вашего опыта.</i>"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Поехали!", callback_data="survey_name")]
        ])
        
        await UXHelper.smooth_edit_text(
            message, 
            final_text, 
            keyboard,
            typing_delay=0.5
        )
    
    @staticmethod
    def format_survey_question(
        question: str, 
        step: int, 
        total_steps: int,
        description: Optional[str] = None
    ) -> str:
        """Форматировать вопрос анкеты"""
        progress = "●" * step + "○" * (total_steps - step)
        
        text = f"<b>Шаг {step} из {total_steps}</b>\n{progress}\n\n"
        text += f"💭 <b>{question}</b>"
        
        if description:
            text += f"\n\n<i>{description}</i>"
            
        return text
    
    @staticmethod
    def create_selection_keyboard(
        items: List[str], 
        callback_prefix: str,
        selected_indices: set = None,
        max_cols: int = 2,
        done_text: str = "✅ Готово"
    ) -> InlineKeyboardMarkup:
        """Создать клавиатуру для выбора из списка с отметками"""
        if selected_indices is None:
            selected_indices = set()
            
        keyboard = []
        
        # Добавляем элементы
        for i in range(0, len(items), max_cols):
            row = []
            for j in range(max_cols):
                if i + j < len(items):
                    item = items[i + j]
                    index = i + j
                    # Добавляем галочку слева если выбран
                    display_text = f"✅ {item}" if str(index) in selected_indices else f"⬜ {item}"
                    row.append(InlineKeyboardButton(
                        text=display_text, 
                        callback_data=f"{callback_prefix}_{index}"
                    ))
            keyboard.append(row)
        
        # Кнопка "Готово"
        keyboard.append([InlineKeyboardButton(text=done_text, callback_data=f"{callback_prefix}_done")])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class AnimatedMessages:
    """Анимированные сообщения для различных сценариев"""
    
    @staticmethod
    async def thinking_animation(message: types.Message, final_text: str):
        """Анимация обдумывания ответа"""
        thinking_steps = [
            "🤔 Обдумываю...",
            "💭 Анализирую ваши слова...",
            "✨ Готовлю ответ..."
        ]
        
        await UXHelper.progress_edit(
            message,
            thinking_steps, 
            final_text,
            step_delay=0.8
        )
    
    @staticmethod
    async def celebration_animation(message: types.Message, text: str):
        """Анимация празднования/завершения"""
        celebration_steps = [
            "🎉 Ура!",
            "✨ Поздравляю!",
            "🌟 Отлично справились!"
        ]
        
        await UXHelper.progress_edit(
            message,
            celebration_steps,
            text,
            step_delay=0.6
        )
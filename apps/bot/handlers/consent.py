from aiogram import Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from shared.models.user import User
from services.user_service import UserService
from services.settings_service import SettingsService
from utils.ux_helper import UXHelper, OnboardingUX, AnimatedMessages


async def consent_accept_handler(callback: types.CallbackQuery):
    telegram_id = str(callback.from_user.id)
    
    async with async_session() as session:
        user_service = UserService(session)
        settings_service = SettingsService(session)
        
        # Get user
        user = await user_service.get_or_create_user(telegram_id)
        
        # Get current policy version
        policy_version = await settings_service.get_setting("policy_version", "v1")
        
        # Accept terms
        await user_service.accept_terms(user, policy_version)
        
        # Log consent event
        await user_service.log_event(user.id, "consent_accepted")
        
        # Beautiful transition message
        await UXHelper.smooth_edit_text(
            callback.message,
            "✨ Отлично! Подготавливаю знакомство...",
            typing_delay=0.3
        )
        
        # Start beautiful survey flow
        await OnboardingUX.survey_intro_animation(callback.message)


async def consent_decline_handler(callback: types.CallbackQuery):
    decline_text = "😔 <b>Понятно...</b>\n\nБез согласия я не могу помочь.\n\nЕсли передумаете — нажмите /start❤️"
    
    await UXHelper.smooth_edit_text(
        callback.message,
        decline_text,
        typing_delay=0.3
    )


async def show_full_policy_handler(callback: types.CallbackQuery):
    async with async_session() as session:
        settings_service = SettingsService(session)
        
        full_policy = await settings_service.get_setting(
            "full_privacy_policy",
            "📄 <b>Политика конфиденциальности</b>\n\n🏥 <b>Что мы делаем:</b>\n• Предоставляем эмоциональную поддержку\n• Помогаем разобраться в чувствах\n• Сохраняем полную анонимность\n\n⚠️ <b>Ограничения:</b>\n• Это не замена психотерапии\n• Мы не врачи и не психологи\n• В кризисе звоните 112 🆘\n\n🛡️ <b>Безопасность:</b>\n• Не сохраняем содержание сообщений\n• Вы можете удалить данные в любое время"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ К началу", callback_data="back_to_consent")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_message")]
    ])
    
    await UXHelper.smooth_edit_text(
        callback.message,
        full_policy, 
        reply_markup=keyboard,
        typing_delay=0.2
    )


async def back_to_consent_handler(callback: types.CallbackQuery):
    user_name = callback.from_user.first_name or "друг"
    
    # ИСПРАВЛЕНО: Убрана долгая анимация, показываем сразу финальный текст
    final_text = f"""🌸 <b>Добро пожаловать, {user_name}!</b>

Ты в безопасном пространстве для души. Здесь можно:
• 💬 Поделиться переживаниями  
• 🧘‍♀️ Найти покой и поддержку
• 📈 Отследить своё эмоциональное состояние

⚠️ <i>Это не замена психотерапии. В кризисных ситуациях звони 112.</i>"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Я согласен продолжить", callback_data="consent_accept"),
            InlineKeyboardButton(text="📋 Условия использования", callback_data="show_full_policy")
        ],
        [
            InlineKeyboardButton(text="❌ Не готов", callback_data="consent_decline")
        ]
    ])
    
    await UXHelper.smooth_edit_text(
        callback.message,
        final_text,
        keyboard,
        typing_delay=0.2
    )


# Function removed - now handled in OnboardingUX.survey_intro_animation


# cancel_message_handler is now universal in dialog.py


def register_consent_handlers(dp: Dispatcher):
    dp.callback_query.register(consent_accept_handler, F.data == "consent_accept")
    dp.callback_query.register(consent_decline_handler, F.data == "consent_decline")
    dp.callback_query.register(show_full_policy_handler, F.data == "show_full_policy")
    dp.callback_query.register(back_to_consent_handler, F.data == "back_to_consent")
    # cancel_message_handler is universal in dialog.py
from aiogram import Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from services.user_service import UserService
from services.settings_service import SettingsService
from shared.models.crisis import CrisisEvent


async def show_crisis_help_handler(callback: types.CallbackQuery):
    """Show crisis help contacts"""
    
    help_text = """🆘 ЭКСТРЕННАЯ ПОМОЩЬ

📞 Всероссийская горячая линия:
8 800 2000 122 (круглосуточно, бесплатно)

🚑 Экстренные службы: 112

💬 Онлайн поддержка:
• Телефон доверия: 8-495-988-44-34
• Чат поддержки: pomogi.org

Если ты в опасности прямо сейчас - звони 112 или обратись к близким людям."""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я в безопасности", callback_data="crisis_safe")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_message")]
    ])
    
    await callback.message.edit_text(help_text, reply_markup=keyboard)


async def crisis_safe_handler(callback: types.CallbackQuery):
    """Handle user confirming they are safe"""
    
    await callback.message.edit_text(
        "Напишите: 'Я не причиню себе вред' чтобы подтвердить, что вы в безопасности"
    )


async def handle_crisis_resolution(message: types.Message):
    """Handle crisis resolution phrase"""
    
    safety_phrases = [
        "я не причиню себе вред",
        "я не причиню себе вреда", 
        "не причиню себе вред",
        "не причиню вред"
    ]
    
    user_text = message.text.lower().strip()
    
    if any(phrase in user_text for phrase in safety_phrases):
        telegram_id = str(message.from_user.id)
        
        async with async_session() as session:
            user_service = UserService(session)
            
            # Get user
            user = await user_service.get_or_create_user(telegram_id)
            
            if user.is_in_crisis:
                # Mark user as safe
                user.is_in_crisis = False
                user.crisis_freeze_until = None
                
                # Log crisis resolution
                await user_service.log_event(user.id, "crisis_resolved")
                
                # Create crisis event record
                crisis_event = CrisisEvent(
                    user_id=user.id,
                    is_resolved=True,
                    resolved_at=datetime.utcnow(),
                    resolution_method="safety_phrase",
                    user_confirmed_safety=True
                )
                session.add(crisis_event)
                
                await session.commit()
                
                await message.answer(
                    "✅ Спасибо за подтверждение. Я рядом, если ты захочешь поговорить."
                )
                return True
    
    return False


# cancel_message_handler is now universal in dialog.py


def register_crisis_handlers(dp: Dispatcher):
    dp.callback_query.register(show_crisis_help_handler, F.data == "show_crisis_help")
    dp.callback_query.register(crisis_safe_handler, F.data == "crisis_safe")
    # cancel_message_handler is universal in dialog.py
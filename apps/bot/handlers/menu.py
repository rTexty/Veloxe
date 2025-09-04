from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from services.user_service import UserService


async def show_main_menu() -> ReplyKeyboardMarkup:
    """Create main reply keyboard menu"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🙋 Мой профиль"),
                KeyboardButton(text="💳 Подписка"),
                KeyboardButton(text="ℹ️ Помощь")
            ],
            [
                KeyboardButton(text="💭 Продолжить"),
                KeyboardButton(text="🔄 Новая тема")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard


async def menu_handler(message: types.Message):
    """Show main menu (/menu command)"""
    
    telegram_id = str(message.from_user.id)
    
    async with async_session() as session:
        user_service = UserService(session)
        user = await user_service.get_or_create_user(telegram_id)
        
        # Check if user completed onboarding
        if not user.terms_accepted or not user.name:
            await message.answer("Пожалуйста, сначала завершите регистрацию: /start")
            return
    
    main_menu = await show_main_menu()


async def handle_unknown_command(message: types.Message):
    """Handle unknown commands and provide help"""
    
    if message.text and message.text.startswith('/'):
        await message.answer(
            "❓ Неизвестная команда.\n\n"
            "Доступные команды:\n"
            "• /start — начать работу\n"
            "• /profile — мой профиль\n"
            "• /menu — главное меню\n"
            "• /help — помощь"
        )


async def continue_dialog_handler(message: types.Message):
    """Handle 'Продолжить' button - generate next GPT response without new input"""
    from .dialog import dialog_message_handler
    
    # Create a fake message to trigger dialog continuation
    fake_message = message
    fake_message.text = "Продолжи, пожалуйста"
    
    await dialog_message_handler(fake_message)


async def new_topic_handler(message: types.Message):
    """Handle 'Новая тема' button - ask for confirmation and start new session"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    confirm_text = "🔄 <b>Новая тема</b>\n\nСвернуть текущую тему и начать обсуждение чего-то нового?"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, новая тема", callback_data="confirm_new_topic"),
            InlineKeyboardButton(text="❌ Остаться здесь", callback_data="cancel_new_topic")
        ]
    ])
    
    await message.answer(confirm_text, reply_markup=keyboard, parse_mode="HTML")


async def confirm_new_topic_handler(callback: types.CallbackQuery):
    """Confirm starting new topic"""
    telegram_id = str(callback.from_user.id)
    
    async with async_session() as session:
        user_service = UserService(session)
        from services.conversation_service import ConversationService
        conv_service = ConversationService(session)
        
        user = await user_service.get_or_create_user(telegram_id)
        
        # Close current conversation
        conversation = await conv_service.get_or_create_active_conversation(user)
        await conv_service.close_conversation(conversation)
        
        await callback.message.edit_text(
            "✨ <b>Новая тема начата!</b>\n\nО чём хотите поговорить?",
            parse_mode="HTML"
        )


async def cancel_new_topic_handler(callback: types.CallbackQuery):
    """Cancel new topic"""
    await callback.message.edit_text(
        "🔄 <b>Продолжаем текущую тему</b>\n\nЧто у вас на душе?",
        parse_mode="HTML"
    )


def register_menu_handlers(dp: Dispatcher):
    dp.message.register(menu_handler, Command("menu"))
    dp.message.register(handle_unknown_command, F.text.startswith("/"))
    
    # Dialog control buttons
    dp.message.register(continue_dialog_handler, F.text == "💭 Продолжить")
    dp.message.register(new_topic_handler, F.text == "🔄 Новая тема")
    
    # Callback handlers for new topic confirmation
    dp.callback_query.register(confirm_new_topic_handler, F.data == "confirm_new_topic")
    dp.callback_query.register(cancel_new_topic_handler, F.data == "cancel_new_topic")
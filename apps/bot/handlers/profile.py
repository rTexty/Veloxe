from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, desc
from datetime import datetime
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from shared.models.user import User
from shared.models.subscription import Subscription
from services.user_service import UserService
from services.conversation_service import ConversationService


class ProfileStates(StatesGroup):
    waiting_delete_confirmation = State()


async def show_main_menu():
    """Create main menu keyboard"""
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
        persistent=True
    )
    return keyboard


async def profile_handler(message: types.Message):
    """Show user profile (/profile command or menu button)"""
    telegram_id = str(message.from_user.id)
    
    async with async_session() as session:
        user_service = UserService(session)
        
        # Get user with subscription
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("Пожалуйста, начните с команды /start")
            return
        
        # Get subscription info
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(desc(Subscription.created_at))
        )
        subscription = result.scalar_one_or_none()
        
        # Build profile text
        profile_text = "👤 **Мой профиль**\n\n"
        
        # Basic info
        profile_text += f"**Имя:** {user.name or '—'}\n"
        profile_text += f"**Возраст:** {user.age or '—'}\n"
        
        gender_map = {"male": "Мужской", "female": "Женский", "not_applicable": "Не важно"}
        profile_text += f"**Пол:** {gender_map.get(user.gender, '—')}\n"
        profile_text += f"**Город:** {user.city or '—'}"
        
        if user.timezone:
            profile_text += f" ({user.timezone})"
        profile_text += "\n\n"
        
        # Emotions and topics
        if user.emotion_tags:
            emotions_text = ", ".join([tag.split(" ", 1)[1] if " " in tag else tag for tag in user.emotion_tags[:5]])
            if len(user.emotion_tags) > 5:
                emotions_text += "..."
            profile_text += f"**Эмоции:** {emotions_text}\n"
        
        if user.topic_tags:
            topics_text = ", ".join([tag.split(" ", 1)[1] if " " in tag else tag for tag in user.topic_tags[:5]])
            if len(user.topic_tags) > 5:
                topics_text += "..."
            profile_text += f"**Темы:** {topics_text}\n"
        
        # Subscription status
        profile_text += "\n**💳 Подписка:**\n"
        if subscription and subscription.is_active and subscription.ends_at > datetime.utcnow():
            profile_text += f"✅ Активна до {subscription.ends_at.strftime('%d.%m.%Y')}"
        elif subscription:
            if subscription.ends_at < datetime.utcnow():
                profile_text += f"❌ Истекла {subscription.ends_at.strftime('%d.%m.%Y')}"
            else:
                profile_text += "❌ Не активна"
        else:
            profile_text += "❌ Не активна"
        
        # Daily messages info for free users
        if subscription and (not subscription.is_active or subscription.ends_at <= datetime.utcnow()):
            profile_text += f"\n📝 Сообщений сегодня: {subscription.daily_messages_used}/{subscription.daily_messages_limit}"
        
        # Profile action buttons
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Изменить", callback_data="profile_edit"),
                InlineKeyboardButton(text="🧹 Очистить историю", callback_data="profile_clear_history")
            ],
            [
                InlineKeyboardButton(text="🗑 Удалить данные", callback_data="profile_delete_data"),
                InlineKeyboardButton(text="🚫 Удалить профиль", callback_data="profile_delete_profile")
            ]
        ])
        
        # Set main menu keyboard
        main_menu = await show_main_menu()
        
        await message.answer(profile_text, reply_markup=keyboard, parse_mode="Markdown")
        await message.answer("Выберите действие:", reply_markup=main_menu)


async def profile_edit_handler(callback: types.CallbackQuery):
    """Handle profile edit button"""
    await callback.message.edit_text(
        "Для изменения профиля пройдите анкету заново:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Пройти анкету", callback_data="survey_name")],
            [InlineKeyboardButton(text="◀️ Назад к профилю", callback_data="back_to_profile")]
        ])
    )


async def profile_clear_history_handler(callback: types.CallbackQuery):
    """Handle clear conversation history"""
    telegram_id = str(callback.from_user.id)
    
    async with async_session() as session:
        user_service = UserService(session)
        conv_service = ConversationService(session)
        
        user = await user_service.get_or_create_user(telegram_id)
        
        # Clear conversation history
        await conv_service.clear_conversation_history(user)
        
        # Log event
        await user_service.log_event(user.id, "history_cleared")
    
    await callback.message.edit_text("🧹 История диалогов очищена. Анкета и подписка сохранены.")


async def profile_delete_data_handler(callback: types.CallbackQuery):
    """Handle soft delete (clear profile data but keep subscription)"""
    await callback.message.edit_text(
        "⚠️ **Удаление данных**\n\nБудут удалены:\n• Анкетные данные\n• История диалогов\n\n"
        "Сохранится:\n• Подписка\n• Базовая запись пользователя\n\n"
        "Продолжить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data="confirm_delete_data"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_profile")
            ]
        ]),
        parse_mode="Markdown"
    )


async def confirm_delete_data_handler(callback: types.CallbackQuery):
    """Confirm soft delete"""
    telegram_id = str(callback.from_user.id)
    
    async with async_session() as session:
        user_service = UserService(session)
        conv_service = ConversationService(session)
        
        user = await user_service.get_or_create_user(telegram_id)
        
        # Clear profile data
        user.name = None
        user.age = None
        user.gender = None
        user.city = None
        user.timezone = None
        user.emotion_tags = None
        user.topic_tags = None
        
        # Clear conversation history
        await conv_service.clear_conversation_history(user)
        
        await session.commit()
        
        # Log event
        await user_service.log_event(user.id, "data_deleted")
    
    await callback.message.edit_text("🗑 Данные удалены. Подписка сохранена. Для продолжения используйте /start")


async def profile_delete_profile_handler(callback: types.CallbackQuery, state: FSMContext):
    """Handle hard delete warning"""
    await callback.message.edit_text(
        "🚫 **ПОЛНОЕ УДАЛЕНИЕ ПРОФИЛЯ**\n\n"
        "⚠️ Это действие необратимо!\n\n"
        "Будет удалено ВСЁ:\n"
        "• Анкетные данные\n"
        "• История диалогов\n"
        "• Подписка\n"
        "• Все записи о вас\n\n"
        "💰 Деньги за неиспользованную подписку НЕ возвращаются автоматически.\n\n"
        "Для подтверждения напишите: **DELETE**",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_profile")]
        ]),
        parse_mode="Markdown"
    )
    
    await state.set_state(ProfileStates.waiting_delete_confirmation)


async def handle_delete_confirmation(message: types.Message, state: FSMContext):
    """Handle DELETE confirmation"""
    if message.text and message.text.upper().strip() == "DELETE":
        telegram_id = str(message.from_user.id)
        
        async with async_session() as session:
            # Complete hard delete
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Delete all related data (cascade should handle this)
                await session.delete(user)
                await session.commit()
        
        await message.answer(
            "🚫 Профиль полностью удален.\n\n"
            "Спасибо что были с нами. Если захотите вернуться - всегда добро пожаловать! /start"
        )
        await state.clear()
    else:
        await message.answer(
            "❌ Неверное подтверждение. Для удаления напишите точно: **DELETE**\n\n"
            "Или нажмите /profile для возврата к профилю.",
            parse_mode="Markdown"
        )


async def back_to_profile_handler(callback: types.CallbackQuery, state: FSMContext):
    """Return to profile view"""
    await state.clear()
    await profile_handler(callback.message)


async def subscription_menu_handler(message: types.Message):
    """Handle subscription menu button"""
    telegram_id = str(message.from_user.id)
    
    async with async_session() as session:
        user_service = UserService(session)
        user = await user_service.get_or_create_user(telegram_id)
        
        # Check if user completed onboarding
        if not user.terms_accepted or not user.name:
            await message.answer("Пожалуйста, сначала завершите регистрацию: /start")
            return
        
        from services.settings_service import SettingsService
        settings_service = SettingsService(session)
        
        # Get subscription plans from admin settings
        plans = await settings_service.get_setting("subscription_plans", [])
        
        # Check if plans are configured
        if not plans:
            await message.answer(
                "⚠️ Тарифы временно недоступны. Попробуйте позже или обратитесь к администратору.",
                parse_mode="Markdown"
            )
            return
        
        # Get user's current subscription
        from shared.models.subscription import Subscription
        from sqlalchemy import select, desc
        
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(desc(Subscription.created_at))
        )
        subscription = result.scalar_one_or_none()
        
        # Build subscription status text
        text = "💳 **Подписка**\n\n"
        
        if subscription and subscription.is_active and subscription.ends_at > datetime.utcnow():
            text += f"✅ **Активна до:** {subscription.ends_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        elif subscription and subscription.ends_at < datetime.utcnow():
            text += f"❌ **Истекла:** {subscription.ends_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        else:
            text += "❌ **Подписка неактивна**\n\n"
        
        text += "📋 **Доступные тарифы:**\n\n"
        
        # Create keyboard with plans
        keyboard_rows = []
        for plan in plans:
            price_text = f"{plan['price']} {plan['currency']}" if plan['currency'] == 'RUB' else f"${plan['price']:.2f}"
            discount_text = f" (-{plan['discount']}%)" if plan.get('discount', 0) > 0 else ""
            text += f"• **{plan['name']}** — {price_text}{discount_text}\n"
            
            keyboard_rows.append([
                InlineKeyboardButton(
                    text=f"{plan['name']} — {price_text}",
                    callback_data=f"select_plan_{plan['name'].replace(' ', '_')}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")


async def help_handler(message: types.Message):
    """Handle help menu button"""
    help_text = """ℹ️ **Помощь**

**Что это за сервис?**
Veloxe — это эмпатичный бот для эмоциональной поддержки. Я помогаю разобраться в чувствах и найти поддержку в трудные моменты.

**Что я НЕ делаю:**
❌ Не заменяю психотерапию
❌ Не даю медицинских советов
❌ Не ставлю диагнозы

**Как работает:**
• 5 бесплатных сообщений в день
• Подписка для безлимитного общения
• Анонимность и конфиденциальность

**В экстренных ситуациях:**
🚑 Службы экстренной помощи: 112
📞 Горячая линия психологической поддержки: 8 800 2000 122

**Управление данными:**
• Изменить анкету: 🙋 Мой профиль → ✏️ Изменить
• Очистить историю: 🙋 Мой профиль → 🧹 Очистить
• Удалить данные: 🙋 Мой профиль → 🗑 Удалить

**Как отключить пинги:**
• Зайти в 🙋 Мой профиль
• Выбрать настройки уведомлений
• Отключить автоматические пинги

**Оплата Stars:**
• Выбрать 💳 Подписка
• Выбрать нужный тариф
• Оплатить через Telegram Stars
• Подписка активируется автоматически

**Поддержка:**
По вопросам пишите @support"""
    
    await message.answer(help_text, parse_mode="Markdown")


def register_profile_handlers(dp: Dispatcher):
    # Command handlers
    dp.message.register(profile_handler, Command("profile"))
    dp.message.register(help_handler, Command("help"))
    
    # Menu button handlers
    dp.message.register(profile_handler, F.text == "🙋 Мой профиль")
    dp.message.register(subscription_menu_handler, F.text == "💳 Подписка")
    dp.message.register(help_handler, F.text == "ℹ️ Помощь")
    
    # Profile callback handlers
    dp.callback_query.register(profile_edit_handler, F.data == "profile_edit")
    dp.callback_query.register(profile_clear_history_handler, F.data == "profile_clear_history")
    dp.callback_query.register(profile_delete_data_handler, F.data == "profile_delete_data")
    dp.callback_query.register(confirm_delete_data_handler, F.data == "confirm_delete_data")
    dp.callback_query.register(profile_delete_profile_handler, F.data == "profile_delete_profile")
    dp.callback_query.register(back_to_profile_handler, F.data == "back_to_profile")
    
    # Delete confirmation handler
    dp.message.register(handle_delete_confirmation, ProfileStates.waiting_delete_confirmation)
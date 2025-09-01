from aiogram import Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, SuccessfulPayment
from datetime import datetime, timedelta
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from services.user_service import UserService
from services.settings_service import SettingsService
from services.conversation_service import ConversationService
from services.payment_service import PaymentService
from utils.ux_helper import UXHelper


async def show_subscription_handler(callback: types.CallbackQuery):
    """Show subscription plans"""
    
    async with async_session() as session:
        settings_service = SettingsService(session)
        
        plans = await settings_service.get_setting("subscription_plans", [])
    
    if not plans:
        await callback.message.edit_text(
            "⚠️ Тарифы временно недоступны. Попробуйте позже или обратитесь к администратору."
        )
        return
    
    text = "💳 Подписка\n\nВыберите тариф для безлимитного общения:\n\n"
    
    keyboard_rows = []
    for plan in plans:
        price_text = f"${plan['price']:.2f}" if plan['currency'] == 'USD' else f"{plan['price']:.2f} {plan['currency']}"
        text += f"• {plan['days']} дней — {price_text}\n"
        
        keyboard_rows.append([
            InlineKeyboardButton(
                text=f"{plan['days']} дней — {price_text}",
                callback_data=f"select_plan_{plan['name']}"
            )
        ])
    
    keyboard_rows.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_dialog")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    await callback.message.edit_text(text, reply_markup=keyboard)


async def select_plan_handler(callback: types.CallbackQuery):
    """Handle plan selection"""
    
    plan_name = callback.data.replace("select_plan_", "")
    
    async with async_session() as session:
        settings_service = SettingsService(session)
        
        plans = await settings_service.get_setting("subscription_plans", [])
        selected_plan = next((p for p in plans if p['name'] == plan_name), None)
        
        if not selected_plan:
            await callback.answer("План не найден")
            return
    
    price_text = f"${selected_plan['price']:.2f}"
    
    text = f"Выбран тариф: {selected_plan['days']} дней — {price_text}\n\nВыберите способ оплаты:"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Telegram Stars", callback_data=f"pay_stars_{plan_name}")],
        [InlineKeyboardButton(text="Оплатить криптовалютой", callback_data=f"pay_card_{plan_name}")],
        [InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="show_subscription")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)


async def pay_stars_handler(callback: types.CallbackQuery):
    """Handle Telegram Stars payment"""
    
    plan_name = callback.data.replace("pay_stars_", "")
    user_id = callback.from_user.id
    
    payment_service = PaymentService()
    invoice_data, error = await payment_service.create_telegram_stars_invoice(user_id, plan_name)
    
    if error:
        # Truncate error message to avoid MESSAGE_TOO_LONG error
        error_msg = error[:100]  # Limit to 100 characters
        await callback.answer(f"Ошибка: {error_msg}")
        return
    
    try:
        await callback.bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=invoice_data["title"],
            description=invoice_data["description"],
            provider_token=invoice_data["provider_token"],
            currency=invoice_data["currency"],
            prices=invoice_data["prices"],
            start_parameter=invoice_data["start_parameter"],
            payload=invoice_data["payload"]
        )
        
        
    except Exception as e:
        # Truncate error message to avoid MESSAGE_TOO_LONG error
        error_msg = str(e)[:100]  # Limit to 100 characters
        await callback.answer(f"Ошибка создания счета: {error_msg}")
        
        # Fallback to card payment
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="₿ Оплатить криптовалютой", callback_data=f"pay_card_{plan_name}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"select_plan_{plan_name}")]
        ])
        
        await callback.message.edit_text(
            "⭐ Telegram Stars временно недоступны.\n\nПопробуйте оплату картой:",
            reply_markup=keyboard
        )


async def pay_card_handler(callback: types.CallbackQuery):
    """Handle card payment via CryptoCloud"""
    
    plan_name = callback.data.replace("pay_card_", "")
    user_id = callback.from_user.id
    
    # Show loading message
    await UXHelper.smooth_edit_text(
        callback.message,
        "₿ Создаем ссылку для оплаты криптовалютой...",
        typing_delay=1.0
    )
    
    payment_service = PaymentService()
    payment_data, error = await payment_service.create_cryptocloud_invoice(user_id, plan_name)
    
    if error:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars_{plan_name}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"select_plan_{plan_name}")]
        ])
        
        # Truncate error message to avoid MESSAGE_TOO_LONG error
        error_msg = error[:200]  # Limit to 200 characters for longer messages
        await callback.message.edit_text(
            f"❌ {error_msg}\n\nПопробуйте альтернативный способ оплаты:",
            reply_markup=keyboard
        )
        return
    
    # Show payment link
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_data["url"])],
        [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars_{plan_name}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"select_plan_{plan_name}")]
    ])
    
    text = f"""₿ Оплата криптовалютой

Сумма: {payment_data['amount']} RUB

Нажмите кнопку "Оплатить" для перехода к форме оплаты. 
После успешной оплаты ваша подписка будет активирована автоматически.

⚠️ Ссылка действительна в течение 24 часов."""
    
    await callback.message.edit_text(text, reply_markup=keyboard)


async def back_to_dialog_handler(callback: types.CallbackQuery):
    """Return to dialog"""
    await callback.message.edit_text("Продолжаем общение. О чём хотите поговорить?")


async def remind_later_handler(callback: types.CallbackQuery):
    """Handle 'remind later' button from subscription reminders"""
    await callback.answer("Хорошо, напомним позже!")
    await callback.message.edit_text("👍 Понятно, напомним о продлении подписки позже.\n\nПродолжаем общение!")


# Mock function for successful payment (to be replaced with real payment processing)
async def process_successful_payment(user_id: int, plan_name: str, payment_provider: str, payment_id: str):
    """Process successful payment and activate subscription"""
    
    async with async_session() as session:
        user_service = UserService(session)
        settings_service = SettingsService(session)
        conv_service = ConversationService(session)
        
        # Get plan details
        plans = await settings_service.get_setting("subscription_plans", [])
        plan = next((p for p in plans if p['name'] == plan_name), None)
        
        if not plan:
            return False
        
        # Get user
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return False
        
        # Get or create subscription
        from sqlalchemy import select, desc
        from shared.models.user import User
        from shared.models.subscription import Subscription
        
        result = await session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(desc(Subscription.created_at))
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            # Create new subscription
            subscription = Subscription(
                user_id=user_id,
                plan_name=plan['name'],
                price=plan['price'],
                currency=plan.get('currency', 'USD'),
                starts_at=datetime.utcnow(),
                ends_at=datetime.utcnow() + timedelta(days=plan['days']),
                is_active=True,
                payment_provider=payment_provider,
                payment_id=payment_id
            )
            session.add(subscription)
        else:
            # Update existing subscription
            start_time = max(datetime.utcnow(), subscription.ends_at) if subscription.is_active else datetime.utcnow()
            
            subscription.plan_name = plan['name']
            subscription.price = plan['price']
            subscription.currency = plan.get('currency', 'USD')
            subscription.starts_at = start_time
            subscription.ends_at = start_time + timedelta(days=plan['days'])
            subscription.is_active = True
            subscription.payment_provider = payment_provider
            subscription.payment_id = payment_id
            
            # Reset daily limits for paid users
            subscription.daily_messages_used = 0
            subscription.daily_messages_limit = 999999  # Unlimited for subscribers
        
        await session.commit()
        
        # Log payment success
        await user_service.log_event(user_id, "payment_ok", {
            'plan': plan['name'],
            'price': plan['price'],
            'provider': payment_provider
        })
        
        return True


async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Handle pre-checkout query for Telegram Stars"""
    try:
        # Always approve the payment (validation was done during invoice creation)
        await pre_checkout_query.answer(ok=True)
    except Exception as e:
        await pre_checkout_query.answer(
            ok=False, 
            error_message=f"Ошибка обработки платежа: {str(e)}"
        )


async def successful_payment_handler(message: types.Message):
    """Handle successful payment"""
    payment = message.successful_payment
    if not payment:
        return
    
    user_id = message.from_user.id
    payment_service = PaymentService()
    
    try:
        success = await payment_service.process_successful_stars_payment(
            user_id, 
            payment.telegram_payment_charge_id,
            payment.invoice_payload
        )
        
        if success:
            await UXHelper.smooth_answer(
                message,
                "✅ Оплата прошла успешно!\n\nВаша подписка активирована. Теперь у вас безлимитное общение с ботом. Приятного использования! 🎉",
                typing_delay=1.0
            )
        else:
            await UXHelper.smooth_answer(
                message,
                "❌ Произошла ошибка при активации подписки.\n\nОбратитесь в поддержку @support с номером платежа: " + payment.telegram_payment_charge_id,
                typing_delay=0.5
            )
            
    except Exception as e:
        await UXHelper.smooth_answer(
            message,
            f"❌ Ошибка обработки платежа: {str(e)}\n\nОбратитесь в поддержку @support",
            typing_delay=0.5
        )


def register_subscription_handlers(dp: Dispatcher):
    dp.callback_query.register(show_subscription_handler, F.data == "show_subscription")
    dp.callback_query.register(select_plan_handler, F.data.startswith("select_plan_"))
    dp.callback_query.register(pay_stars_handler, F.data.startswith("pay_stars_"))
    dp.callback_query.register(pay_card_handler, F.data.startswith("pay_card_"))
    dp.callback_query.register(back_to_dialog_handler, F.data == "back_to_dialog")
    dp.callback_query.register(remind_later_handler, F.data == "remind_later")
    
    # Payment handlers
    dp.pre_checkout_query.register(pre_checkout_handler)
    dp.message.register(successful_payment_handler, F.successful_payment)
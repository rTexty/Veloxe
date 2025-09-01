from aiogptbot.bot.db.postgres import db
from aiogptbot.bot.config import settings
from aiogram.types import LabeledPrice
from datetime import datetime, timedelta
import httpx
from aiogram import Bot
from loguru import logger
import asyncio
from .error_handling_service import error_handler
from .analytics_service import analytics_service
import uuid


async def create_telegram_invoice(user_id):
    try:
        # Check if in maintenance mode
        if await error_handler.is_in_maintenance_mode():
            return None, error_handler.maintenance_message
            
        row = await db.fetchrow("SELECT value FROM prices WHERE name='premium_month_stars'")
        if not row:
            return None, "Стоимость подписки (Stars) не установлена. Обратитесь к администратору."
        price_in_stars = int(row['value'])
        prices = [LabeledPrice(label="Premium подписка на 1 месяц", amount=price_in_stars)]
        
        # Log paywall shown event
        await analytics_service.log_payment_event('paywall_shown', user_id, 
                                               payment_method='stars')
        
        return {
            "user_id": user_id,
            "title": "Premium подписка",
            "description": "Неограниченный доступ к AI-боту на 1 месяц.",
            "provider_token": "",
            "currency": "XTR",
            "prices": prices,
            "start_parameter": "premium-subscription",
            "payload": f"premium_recharge_user_{user_id}"
        }, None
    except Exception as e:
        logger.error(f"Error creating Telegram invoice for user {user_id}: {e}")
        error_message = await error_handler.handle_payment_error(user_id, e)
        return None, error_message

async def record_successful_telegram_payment(user_id: int, amount: int, telegram_payment_charge_id: str):
    """
    Записывает информацию об успешном платеже через Telegram Stars в базу данных.
    """
    await db.execute(
        """
        INSERT INTO payments (user_id, amount, currency, payment_method, status, created_at, invoice_id)
        VALUES ($1, $2, 'XTR', 'stars', 'success', $3, $4)
        """,
        user_id,
        amount,
        datetime.now(),
        telegram_payment_charge_id,
    )
    
    # Log successful payment event
    await analytics_service.log_payment_event('payment_ok', user_id, 
                                           amount=amount, 
                                           currency='XTR', 
                                           payment_method='stars')
    
    logger.info(f"Recorded successful payment for user_id={user_id}, amount={amount}, charge_id={telegram_payment_charge_id}")

async def create_cryptocloud_invoice(user_id):
    try:
        # Check if in maintenance mode
        if await error_handler.is_in_maintenance_mode():
            return None, error_handler.maintenance_message
            
        row = await db.fetchrow("SELECT value FROM prices WHERE name='premium_month_crypto'")
        if not row:
            return None, "Стоимость подписки (Crypto) не установлена. Обратитесь к администратору."
        price = int(row['value'])
        api_key = settings.CRYPTOCLOUD_API_KEY
        payload = {
            "shop_id": settings.CRYPTOCLOUD_SHOP_ID,
            "amount": price,
            "currency": "RUB",
            "order_id": str(user_id),
            "desc": "Premium подписка на 1 месяц"
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.cryptocloud.plus/v2/invoice/create",
                headers={"Authorization": f"Token {api_key}"},
                json=payload
            )
            data = resp.json()
            if data.get("status") == "success":
                url = data["result"]["link"]
                invoice_id = data["result"]["uuid"]
                user_row = await db.fetchrow("SELECT id FROM users WHERE telegram_id=$1", user_id)
                if not user_row:
                    return None, "Пользователь не найден в базе. Попробуйте позже."
                real_user_id = user_row["id"]
                await db.execute(
                    "INSERT INTO payments (user_id, amount, currency, payment_method, status, created_at, invoice_id) VALUES ($1, $2, $3, 'cryptocloud', 'pending', $4, $5)",
                    real_user_id, price, "RUB", datetime.now(), invoice_id
                )
                
                # Log paywall shown event
                await analytics_service.log_payment_event('paywall_shown', user_id, 
                                                       amount=price, 
                                                       currency="RUB", 
                                                       payment_method='cryptocloud')
                
                return {"url": url, "invoice_id": invoice_id}, None
            else:
                error_msg = data.get("error", "Ошибка при создании ссылки на оплату. Попробуйте позже.")
                return None, error_msg
    except httpx.RequestError as e:
        logger.error(f"Network error creating CryptoCloud invoice for user {user_id}: {e}")
        error_message = await error_handler.handle_payment_error(user_id, e)
        return None, error_message
    except Exception as e:
        logger.error(f"Error creating CryptoCloud invoice for user {user_id}: {e}")
        error_message = await error_handler.handle_payment_error(user_id, e)
        return None, error_message

async def create_sbp_payment(user_id):
    """
    Create SBP payment instruction for the user.
    """
    try:
        # Check if SBP payments are enabled
        enabled_row = await db.fetchrow("SELECT value FROM text_settings WHERE key='sbp_payment_enabled'")
        is_enabled = enabled_row and enabled_row['value'].lower() == 'true'
        
        if not is_enabled:
            return None, "Оплата через СБП временно недоступна."
            
        # Get payment amount
        row = await db.fetchrow("SELECT value FROM prices WHERE name='premium_month_rub'")
        if not row:
            return None, "Стоимость подписки (RUB) не установлена. Обратитесь к администратору."
        amount = int(row['value'])
        
        # Generate unique comment for this payment
        comment = f"VEL-{user_id}-{uuid.uuid4().hex[:8]}"
        
        # Get instruction template
        template_row = await db.fetchrow("SELECT value FROM text_settings WHERE key='sbp_payment_instruction'")
        if template_row and template_row['value']:
            instruction = template_row['value'].replace("{amount}", str(amount)).replace("{phone}", "+79991234567").replace("{comment}", comment)
        else:
            instruction = f"Для оплаты через СБП отправьте {amount} рублей на номер телефона +79991234567. Укажите комментарий \"{comment}\"."
        
        # Log paywall shown event
        await analytics_service.log_payment_event('paywall_shown', user_id, 
                                               amount=amount, 
                                               currency="RUB", 
                                               payment_method='sbp')
        
        # Record pending payment
        user_row = await db.fetchrow("SELECT id FROM users WHERE telegram_id=$1", user_id)
        if user_row:
            real_user_id = user_row["id"]
            await db.execute(
                "INSERT INTO payments (user_id, amount, currency, payment_method, status, created_at, invoice_id) VALUES ($1, $2, 'RUB', 'sbp', 'pending', $3, $4)",
                real_user_id, amount, datetime.now(), comment
            )
        
        return instruction, None
    except Exception as e:
        logger.error(f"Error creating SBP payment for user {user_id}: {e}")
        error_message = await error_handler.handle_payment_error(user_id, e)
        return None, error_message

async def create_yookassa_payment(user_id):
    """
    Create YooKassa payment instruction for the user.
    """
    try:
        # Check if YooKassa payments are enabled
        enabled_row = await db.fetchrow("SELECT value FROM text_settings WHERE key='yookassa_payment_enabled'")
        is_enabled = enabled_row and enabled_row['value'].lower() == 'true'
        
        if not is_enabled:
            return None, "Оплата через YooKassa временно недоступна."
            
        # Get payment amount
        row = await db.fetchrow("SELECT value FROM prices WHERE name='premium_month_rub'")
        if not row:
            return None, "Стоимость подписки (RUB) не установлена. Обратитесь к администратору."
        amount = int(row['value'])
        
        # In a real implementation, this would integrate with YooKassa API
        # For now, we'll just provide a placeholder instruction
        payment_url = f"https://yookassa.example.com/pay?user={user_id}&amount={amount}"
        
        # Get instruction template
        template_row = await db.fetchrow("SELECT value FROM text_settings WHERE key='yookassa_payment_instruction'")
        if template_row and template_row['value']:
            instruction = template_row['value'].replace("{payment_url}", payment_url)
        else:
            instruction = f"Для оплаты через YooKassa перейдите по ссылке: {payment_url}"
        
        # Log paywall shown event
        await analytics_service.log_payment_event('paywall_shown', user_id, 
                                               amount=amount, 
                                               currency="RUB", 
                                               payment_method='yookassa')
        
        # Record pending payment
        user_row = await db.fetchrow("SELECT id FROM users WHERE telegram_id=$1", user_id)
        if user_row:
            real_user_id = user_row["id"]
            await db.execute(
                "INSERT INTO payments (user_id, amount, currency, payment_method, status, created_at, invoice_id) VALUES ($1, $2, 'RUB', 'yookassa', 'pending', $3, $4)",
                real_user_id, amount, datetime.now(), str(uuid.uuid4())
            )
        
        return instruction, None
    except Exception as e:
        logger.error(f"Error creating YooKassa payment for user {user_id}: {e}")
        error_message = await error_handler.handle_payment_error(user_id, e)
        return None, error_message

async def poll_cryptocloud_payments(bot: Bot):
    """
    Запускать как отдельную задачу при старте бота.
    Проверяет все pending-платежи CryptoCloud раз в 20 секунд и активирует подписку при оплате.
    """
    while True:
        try:
            payments = await db.fetch("SELECT * FROM payments WHERE payment_method='cryptocloud' AND status='pending'")
            api_key = settings.CRYPTOCLOUD_API_KEY
            for payment in payments:
                try:
                    invoice_id = payment['invoice_id']
                    user_id = payment['user_id']
                    async with httpx.AsyncClient() as client:
                        resp = await client.post(
                            "https://api.cryptocloud.plus/v2/invoice/merchant/info",
                            headers={"Authorization": f"Token {api_key}"},
                            json={"uuids": [invoice_id]}
                        )
                        data = resp.json()
                        if (
                            data.get("status") == "success"
                            and data.get("result")
                            and isinstance(data["result"], list)
                            and len(data["result"]) > 0
                            and data["result"][0].get("status") in ["paid", "overpaid"]
                        ):
                            # Получаем telegram_id по user_id
                            user_row = await db.fetchrow("SELECT telegram_id FROM users WHERE id=$1", user_id)
                            if not user_row:
                                continue
                            telegram_id = user_row["telegram_id"]
                            until = datetime.now() + timedelta(days=30)
                            await db.execute(
                                "UPDATE users SET status='premium', subscription_until=$1 WHERE telegram_id=$2",
                                until, telegram_id
                            )
                            await db.execute(
                                "INSERT INTO subscriptions (user_id, type, start_date, end_date, is_active) VALUES ($1, 'premium', $2, $3, TRUE)",
                                user_id, datetime.now(), until
                            )
                            updated = await db.execute(
                                "UPDATE payments SET status='success' WHERE id=$1 AND status='pending'",
                                payment['id']
                            )
                            if updated and (updated == 'UPDATE 1' or updated == 'UPDATE 1;'):
                                try:
                                    await bot.send_message(telegram_id, "Ваша подписка активирована! Спасибо за оплату через CryptoCloud. Приятного общения с AI-ботом!")
                                except Exception as e:
                                    logger.warning(f"Не удалось отправить уведомление пользователю {telegram_id}: {e}")
                                
                                # Log successful payment event
                                await analytics_service.log_payment_event('payment_ok', user_id, 
                                                                       amount=payment['amount'], 
                                                                       currency=payment['currency'], 
                                                                       payment_method='cryptocloud')
                        else:
                            # Log payment failure event
                            await analytics_service.log_payment_event('payment_failed', user_id, 
                                                                    amount=payment['amount'], 
                                                                    currency=payment['currency'], 
                                                                    payment_method='cryptocloud')
                except httpx.RequestError as e:
                    logger.error(f"Network error checking payment {payment['id']}: {e}")
                    # Continue with other payments
                    continue
                except Exception as e:
                    logger.error(f"Error checking payment {payment['id']}: {e}")
                    # Continue with other payments
                    continue
            await asyncio.sleep(20) 
        except Exception as e:
            logger.error(f"Error in poll_cryptocloud_payments: {e}")
            # Wait before retrying
            await asyncio.sleep(60)

async def poll_sbp_payments(bot: Bot):
    """
    Check for SBP payments. In a real implementation, this would integrate with a bank API.
    For now, this is a placeholder that shows how it would work.
    """
    while True:
        try:
            # In a real implementation, we would check with a bank API for completed payments
            # For now, we'll just log that this function exists
            logger.info("Checking for SBP payments (placeholder implementation)")
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in poll_sbp_payments: {e}")
            await asyncio.sleep(60)

async def poll_yookassa_payments(bot: Bot):
    """
    Check for YooKassa payments. In a real implementation, this would integrate with YooKassa API.
    For now, this is a placeholder that shows how it would work.
    """
    while True:
        try:
            # In a real implementation, we would check with YooKassa API for completed payments
            # For now, we'll just log that this function exists
            logger.info("Checking for YooKassa payments (placeholder implementation)")
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Error in poll_yookassa_payments: {e}")
            await asyncio.sleep(60)
"""
Payment service for handling CryptoCloud and Telegram Stars payments
"""
import asyncio
import json
import uuid
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from aiogram import Bot
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from shared.models.user import User
from shared.models.subscription import Subscription
from .settings_service import SettingsService
from .user_service import UserService
from utils.ux_helper import UXHelper
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self):
        pass
    
    async def create_telegram_stars_invoice(self, user_id: int, plan_name: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Create Telegram Stars invoice"""
        try:
            async with async_session() as session:
                settings_service = SettingsService(session)
                
                # Get subscription plans
                plans = await settings_service.get_setting("subscription_plans", [])
                selected_plan = next((p for p in plans if p['name'] == plan_name), None)
                
                if not selected_plan:
                    return None, "План не найден"
                
                # Convert price to Stars (assuming 1 USD = 100 Stars approximate rate)
                price_in_stars = int(float(selected_plan['price'] ) / 0.01569)
                
                prices = [LabeledPrice(
                    label=f"Premium подписка на {selected_plan['days']} дней", 
                    amount=price_in_stars
                )]
                
                # Get or create user first to ensure they exist in the database
                user_service = UserService(session)
                user = await user_service.get_or_create_user(str(user_id))
                
                # Log payment attempt using the internal database user ID
                await user_service.log_event(user.id, "payment_attempt", {
                    'plan': plan_name,
                    'method': 'stars',
                    'price': selected_plan['price']
                })
                
                return {
                    "title": "Premium подписка Veloxe",
                    "description": f"Неограниченное общение с AI-ботом на {selected_plan['days']} дней",
                    "provider_token": "",  # Empty for Telegram Stars
                    "currency": "XTR",
                    "prices": prices,
                    "start_parameter": f"premium-{plan_name}",
                    "payload": f"veloxe_premium_{user_id}_{plan_name}_{uuid.uuid4().hex[:8]}"
                }, None
                
        except Exception as e:
            logger.error(f"Error creating Stars invoice for user {user_id}: {e}")
            return None, f"Ошибка создания счета: {str(e)}"
    
    async def create_cryptocloud_invoice(self, user_id: int, plan_name: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Create CryptoCloud payment invoice"""
        try:
            async with async_session() as session:
                settings_service = SettingsService(session)
                
                # Get subscription plans and CryptoCloud settings
                plans = await settings_service.get_setting("subscription_plans", [])
                selected_plan = next((p for p in plans if p['name'] == plan_name), None)
                
                if not selected_plan:
                    return None, "План не найден"
                
                # Get CryptoCloud API credentials
                api_key = await settings_service.get_setting("cryptocloud_api_key", "")
                shop_id = await settings_service.get_setting("cryptocloud_shop_id", "")
                
                if not api_key or not shop_id:
                    return None, "CryptoCloud не настроен. Обратитесь к администратору"
                
                # Convert price to RUB (assuming USD to RUB conversion rate)
                price_rub = int(selected_plan['price'] * 90)  # Approximate conversion
                order_id = f"{user_id}_{plan_name}_{uuid.uuid4().hex[:8]}"
                
                payload = {
                    "shop_id": shop_id,
                    "amount": price_rub,
                    "currency": "RUB",
                    "order_id": order_id,
                    "desc": f"Premium подписка Veloxe на {selected_plan['days']} дней"
                }
                
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        "https://api.cryptocloud.plus/v2/invoice/create",
                        headers={"Authorization": f"Token {api_key}"},
                        json=payload
                    )
                    
                    data = response.json()
                    
                    if data.get("status") == "success":
                        invoice_id = data["result"]["uuid"]
                        payment_url = data["result"]["link"]
                        
                        # Get or create user first to ensure they exist in the database
                        user_service = UserService(session)
                        user = await user_service.get_or_create_user(str(user_id))
                        
                        subscription = Subscription(
                            user_id=user.id,
                            plan_name=selected_plan['name'],
                            price=price_rub,
                            currency="RUB",
                            starts_at=datetime.utcnow(),
                            ends_at=datetime.utcnow() + timedelta(days=selected_plan['days']),
                            is_active=False,  # Will be activated after payment
                            payment_provider="cryptocloud",
                            payment_id=invoice_id
                        )
                        session.add(subscription)
                        await session.commit()
                        
                        # Log payment attempt using the internal database user ID
                        await user_service.log_event(user.id, "payment_attempt", {
                            'plan': plan_name,
                            'method': 'cryptocloud',
                            'price': price_rub,
                            'invoice_id': invoice_id
                        })
                        
                        return {
                            "url": payment_url,
                            "invoice_id": invoice_id,
                            "amount": price_rub
                        }, None
                    else:
                        error_msg = data.get("error", "Ошибка при создании платежа")
                        logger.error(f"CryptoCloud error: {error_msg}")
                        return None, f"Не удалось создать платеж: {error_msg}"
                        
        except httpx.TimeoutException:
            logger.error(f"Timeout creating CryptoCloud invoice for user {user_id}")
            return None, "Таймаут при создании платежа. Попробуйте позже"
        except Exception as e:
            logger.error(f"Error creating CryptoCloud invoice for user {user_id}: {e}")
            # Truncate error message to avoid MESSAGE_TOO_LONG error
            error_str = str(e)[:100]  # Limit to 100 characters
            return None, f"Ошибка создания платежа: {error_str}"
    
    async def process_successful_stars_payment(self, user_id: int, payment_charge_id: str, payload: str) -> bool:
        """Process successful Telegram Stars payment"""
        try:
            # Extract plan from payload
            if not payload.startswith("veloxe_premium_"):
                logger.error(f"Invalid payment payload: {payload}")
                return False
            
            parts = payload.split("_")
            if len(parts) < 4:
                logger.error(f"Invalid payload format: {payload}")
                return False
            
            plan_name = parts[3]
            
            async with async_session() as session:
                settings_service = SettingsService(session)
                user_service = UserService(session)
                
                # Get plan details
                plans = await settings_service.get_setting("subscription_plans", [])
                plan = next((p for p in plans if p['name'] == plan_name), None)
                
                if not plan:
                    logger.error(f"Plan not found: {plan_name}")
                    return False
                
                # Get or create user
                user = await user_service.get_or_create_user(str(user_id))
                
                # Create or update subscription
                result = await session.execute(
                    select(Subscription)
                    .where(Subscription.user_id == user.id)
                    .order_by(desc(Subscription.created_at))
                )
                subscription = result.scalar_one_or_none()
                
                if not subscription:
                    subscription = Subscription(
                        user_id=user.id,
                        plan_name=plan['name'],
                        price=plan['price'],
                        currency="XTR",
                        starts_at=datetime.utcnow(),
                        ends_at=datetime.utcnow() + timedelta(days=plan['days']),
                        is_active=True,
                        payment_provider="telegram_stars",
                        payment_id=payment_charge_id
                    )
                    session.add(subscription)
                else:
                    # Extend existing subscription
                    start_time = max(datetime.utcnow(), subscription.ends_at) if subscription.is_active else datetime.utcnow()
                    subscription.plan_name = plan['name']
                    subscription.price = plan['price']
                    subscription.currency = "XTR"
                    subscription.starts_at = start_time
                    subscription.ends_at = start_time + timedelta(days=plan['days'])
                    subscription.is_active = True
                    subscription.payment_provider = "telegram_stars"
                    subscription.payment_id = payment_charge_id
                
                await session.commit()
                
                # Log successful payment
                await user_service.log_event(user_id, "payment_ok", {
                    'plan': plan['name'],
                    'price': plan['price'],
                    'method': 'telegram_stars',
                    'charge_id': payment_charge_id
                })
                
                logger.info(f"Successfully processed Stars payment for user {user_id}, plan {plan_name}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing Stars payment for user {user_id}: {e}")
            return False
    
    async def check_cryptocloud_payment_status(self, invoice_id: str) -> Dict[str, Any]:
        """Check CryptoCloud payment status"""
        try:
            async with async_session() as session:
                settings_service = SettingsService(session)
                api_key = await settings_service.get_setting("cryptocloud_api_key", "")
                
                if not api_key:
                    return {"status": "error", "message": "API key not configured"}
                
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.post(
                        "https://api.cryptocloud.plus/v2/invoice/merchant/info",
                        headers={"Authorization": f"Token {api_key}"},
                        json={"uuids": [invoice_id]}
                    )
                    
                    data = response.json()
                    
                    if data.get("status") == "success" and data.get("result"):
                        payment_info = data["result"][0]
                        return {
                            "status": "success",
                            "payment_status": payment_info.get("status"),
                            "amount": payment_info.get("amount"),
                            "currency": payment_info.get("currency")
                        }
                    else:
                        return {"status": "error", "message": "Payment not found"}
                        
        except Exception as e:
            logger.error(f"Error checking CryptoCloud payment status: {e}")
            return {"status": "error", "message": str(e)}
    
    async def process_cryptocloud_webhook(self, webhook_data: Dict) -> bool:
        """Process CryptoCloud webhook notification"""
        try:
            invoice_id = webhook_data.get("invoice_id")
            status = webhook_data.get("status")
            
            if not invoice_id or status not in ["paid", "overpaid"]:
                return False
            
            async with async_session() as session:
                # Find subscription by payment_id
                result = await session.execute(
                    select(Subscription)
                    .where(Subscription.payment_id == invoice_id)
                    .where(Subscription.is_active == False)
                )
                subscription = result.scalar_one_or_none()
                
                if not subscription:
                    logger.warning(f"Subscription not found for invoice {invoice_id}")
                    return False
                
                # Activate subscription
                subscription.is_active = True
                await session.commit()
                
                # Log successful payment
                user_service = UserService(session)
                await user_service.log_event(subscription.user_id, "payment_ok", {
                    'plan': subscription.plan_name,
                    'price': float(subscription.price),
                    'method': 'cryptocloud',
                    'invoice_id': invoice_id
                })
                
                logger.info(f"Successfully activated subscription for invoice {invoice_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing CryptoCloud webhook: {e}")
            return False
"""
Payment webhook router for handling external payment notifications
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import hashlib
import hmac
import httpx
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.config.database import get_db, async_session
from shared.config.settings import settings

# Simplified payment processing for webhooks
from shared.models.user import User
from shared.models.subscription import Subscription
from sqlalchemy import select, update
from datetime import datetime, timedelta

router = APIRouter()


@router.post("/cryptocloud/webhook")
async def cryptocloud_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle CryptoCloud payment webhook"""
    try:
        # Get raw body for signature verification
        raw_body = await request.body()
        webhook_data = json.loads(raw_body)
        
        # Verify webhook signature (optional but recommended)
        # signature = request.headers.get('X-Webhook-Signature')
        # if not verify_cryptocloud_signature(raw_body, signature):
        #     raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Process the webhook - simplified version
        success = await process_cryptocloud_payment(db, webhook_data)
        
        if success:
            return {"status": "ok", "message": "Payment processed successfully"}
        else:
            return {"status": "error", "message": "Payment processing failed"}
            
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


@router.get("/cryptocloud/status/{invoice_id}")
async def check_cryptocloud_status(
    invoice_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Check CryptoCloud payment status manually"""
    try:
        # Direct API call to check status
        async with httpx.AsyncClient(timeout=30) as client:
            # This would need the API key from settings
            # For now, return a simple response
            return {"status": "not_implemented", "message": "Use polling service instead"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check error: {str(e)}")


def verify_cryptocloud_signature(payload: bytes, signature: str, secret_key: str) -> bool:
    """Verify CryptoCloud webhook signature"""
    try:
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False


async def process_cryptocloud_payment(db: AsyncSession, webhook_data: dict) -> bool:
    """Process CryptoCloud payment webhook"""
    try:
        status = webhook_data.get('status')
        if status not in ['paid', 'overpaid']:
            return False
            
        invoice_id = webhook_data.get('uuid')
        order_id = webhook_data.get('order_id')
        
        if not invoice_id:
            return False
            
        # Find user's subscription by payment_id (invoice_id)
        result = await db.execute(
            select(Subscription)
            .where(Subscription.payment_id == invoice_id)
            .where(Subscription.is_active == False)
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            # Activate subscription using update statement
            await db.execute(
                update(Subscription)
                .where(Subscription.id == subscription.id)
                .values(
                    is_active=True,
                    starts_at=datetime.utcnow()
                )
            )
            await db.commit()
            
            # Send notification to user via bot
            await send_payment_success_notification(db, subscription.user_id, subscription.plan_name)
            
            return True
            
        return False
        
    except Exception as e:
        print(f"Error processing CryptoCloud payment: {e}")
        return False


async def send_payment_success_notification(db: AsyncSession, user_id: int, plan_name: str):
    """Send payment success notification to user via bot"""
    try:
        import httpx
        from shared.config.settings import settings
        
        # Get user's telegram_id
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user and user.telegram_id:
            # Send message via bot API (simpler than importing the full bot instance)
            message = "✅ Оплата прошла успешно!\n\nВаша подписка активирована. Теперь у вас безлимитное общение с ботом. Приятного использования! 🎉"
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                    json={
                        "chat_id": str(user.telegram_id),
                        "text": message,
                        "parse_mode": "HTML"
                    },
                    timeout=10
                )
                    
    except Exception as e:
        print(f"Error sending payment notification: {e}")
        # Don't fail the webhook if notification fails
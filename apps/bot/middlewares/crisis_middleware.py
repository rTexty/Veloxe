from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from datetime import datetime
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from services.user_service import UserService
from handlers.crisis import handle_crisis_resolution


class CrisisMiddleware(BaseMiddleware):
    """Middleware to handle users in crisis mode"""
    
    def __init__(self):
        super().__init__()
        # Commands that are always allowed even in crisis mode
        self.allowed_in_crisis = {
            'show_crisis_help', 'crisis_safe', 'start'
        }
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        telegram_id = str(event.from_user.id)
        
        async with async_session() as session:
            user_service = UserService(session)
            user = await user_service.get_or_create_user(telegram_id)
            
            # Check if user is in crisis mode
            if user.is_in_crisis:
                # Check if crisis freeze period is over
                if user.crisis_freeze_until and datetime.utcnow() > user.crisis_freeze_until:
                    # Automatically resolve crisis after freeze period
                    user.is_in_crisis = False
                    user.crisis_freeze_until = None
                    await user_service.log_event(user.id, "crisis_auto_resolved")
                    await session.commit()
                else:
                    # User is still in crisis - check if they're trying to resolve it
                    if isinstance(event, Message):
                        # Check if user is sending safety phrase
                        was_resolved = await handle_crisis_resolution(event)
                        if was_resolved:
                            return  # Crisis resolved, stop here
                        
                        # Check for allowed actions
                        if event.text and not any(cmd in event.text for cmd in self.allowed_in_crisis):
                            # Block regular conversation in crisis mode
                            await event.answer(
                                "🤗 <b>Я рядом с тобой</b>\n\n"
                                "Пока ты в безопасном режиме. Когда будешь готов продолжить — напиши фразу подтверждения или нажми кнопку помощи.",
                                parse_mode="HTML"
                            )
                            return  # Block further processing
                    
                    elif isinstance(event, CallbackQuery):
                        # Allow only crisis-related callbacks
                        if event.data not in self.allowed_in_crisis:
                            await event.answer("Сначала подтвердите, что вы в безопасности")
                            return
        
        # User not in crisis or action is allowed - proceed normally
        return await handler(event, data)
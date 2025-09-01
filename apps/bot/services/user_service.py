from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
import sys
sys.path.append('../../../')

from shared.models.user import User
from shared.models.subscription import Subscription
from shared.models.analytics import Event


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_user(self, telegram_id: str) -> User:
        # Try to get existing user
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            user = User(telegram_id=telegram_id)
            self.session.add(user)
            await self.session.flush()  # Get the user ID without committing
            
            # Create subscription record for daily free usage tracking
            subscription = Subscription(
                user_id=user.id,
                plan_name="free",
                price=0,
                starts_at=datetime.utcnow(),
                ends_at=datetime.utcnow(),  # Free plan "expires" immediately
                is_active=False,
                daily_messages_used=0,
                daily_messages_limit=5,  # Default 5 messages per day
                daily_reset_at=datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            )
            self.session.add(subscription)
            
            await self.session.commit()
            await self.session.refresh(user)
        
        return user
    
    async def accept_terms(self, user: User, policy_version: str):
        user.terms_accepted = True
        user.privacy_accepted = True
        user.policy_version = policy_version
        user.accepted_at = datetime.utcnow()
        await self.session.commit()
    
    async def get_user_by_telegram_id(self, telegram_id: str) -> User:
        """Get user by telegram_id"""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def log_event(self, user_id: int, event_type: str, properties: dict = None):
        event = Event(
            user_id=user_id,
            event_type=event_type,
            properties=properties
        )
        self.session.add(event)
        await self.session.commit()
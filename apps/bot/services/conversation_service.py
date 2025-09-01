import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Dict, Optional
import sys
sys.path.append('../../../')

from shared.models.user import User
from shared.models.conversation import Conversation, Message
from shared.models.subscription import Subscription
from shared.config.redis import RedisCache
from .memory_service import MemoryService


class ConversationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = RedisCache()
        self.memory_service = MemoryService(session)
    
    async def get_or_create_active_conversation(self, user: User) -> Conversation:
        """Get user's active conversation or create new one"""
        
        # Try to find active conversation
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id, Conversation.is_active == True)
            .order_by(desc(Conversation.created_at))
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            # Create new conversation
            session_id = str(uuid.uuid4())
            conversation = Conversation(
                user_id=user.id,
                session_id=session_id,
                is_active=True
            )
            self.session.add(conversation)
            await self.session.commit()
            await self.session.refresh(conversation)
        
        return conversation
    
    async def add_message(
        self, 
        conversation: Conversation, 
        role: str, 
        content: str,
        token_count: Optional[int] = None,
        is_crisis_related: bool = False
    ) -> Message:
        """Add message to conversation"""
        
        message = Message(
            conversation_id=conversation.id,
            role=role,
            content=content,
            token_count=token_count,
            is_crisis_related=is_crisis_related
        )
        
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        
        return message
    
    async def get_conversation_history(
        self, 
        conversation: Conversation, 
        limit: int = 20
    ) -> List[Dict]:
        """Get recent messages from conversation with Redis caching"""
        
        # Try Redis cache first
        cached_messages = await self.cache.get_conversation_cache(conversation.user_id)
        
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        messages = result.scalars().all()
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        message_list = [
            {
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at,
                'token_count': msg.token_count
            }
            for msg in messages
        ]
        
        # Update cache with recent messages
        if message_list:
            await self.cache.set_conversation_cache(
                conversation.user_id,
                {
                    'messages': message_list[-10:],  # Cache last 10 messages
                    'last_update': datetime.utcnow().isoformat(),
                    'conversation_id': conversation.id
                },
                ttl=3600  # 1 hour
            )
        
        return message_list
    
    async def close_conversation(self, conversation: Conversation):
        """Close active conversation and create summary + memory anchors"""
        conversation.is_active = False
        conversation.is_closed = True
        conversation.closed_at = datetime.utcnow()
        await self.session.commit()
        
        # Create conversation summary and memory anchors
        try:
            await self.memory_service.create_conversation_summary(conversation)
        except Exception as e:
            print(f"Error creating conversation summary: {e}")
        
        # Clear Redis cache for this user
        await self.cache.clear_conversation_cache(conversation.user_id)
    
    async def can_user_send_message(self, user: User) -> Dict:
        """Check if user can send message (daily limit or subscription)"""
        
        # Get user's subscription
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(desc(Subscription.created_at))
        )
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return {'can_send': False, 'reason': 'no_subscription'}
        
        # Check if subscription is active (unlimited messages)
        if subscription.is_active and subscription.ends_at > datetime.utcnow():
            return {'can_send': True, 'reason': 'active_subscription'}
        
        # Reset daily limit if needed
        await self._reset_daily_limit_if_needed(subscription)
        
        # Check daily free messages limit
        if subscription.daily_messages_used < subscription.daily_messages_limit:
            return {
                'can_send': True, 
                'reason': 'daily_free_limit',
                'remaining': subscription.daily_messages_limit - subscription.daily_messages_used
            }
        
        return {
            'can_send': False, 
            'reason': 'daily_limit_exceeded',
            'used': subscription.daily_messages_used,
            'limit': subscription.daily_messages_limit
        }
    
    async def _reset_daily_limit_if_needed(self, subscription: Subscription):
        """Reset daily message limit if 24 hours have passed"""
        now = datetime.utcnow()
        
        # If no reset time set or 24 hours have passed
        if (not subscription.daily_reset_at or 
            now >= subscription.daily_reset_at):
            
            subscription.daily_messages_used = 0
            subscription.daily_reset_at = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            await self.session.commit()
    
    async def consume_daily_message(self, user: User):
        """Consume one daily message from user's limit"""
        
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(desc(Subscription.created_at))
        )
        subscription = result.scalar_one_or_none()
        
        if subscription:
            # Reset daily limit if needed
            await self._reset_daily_limit_if_needed(subscription)
            
            # Only consume if not on active subscription and under limit
            if (not subscription.is_active or subscription.ends_at <= datetime.utcnow()) and \
               subscription.daily_messages_used < subscription.daily_messages_limit:
                subscription.daily_messages_used += 1
                await self.session.commit()
    
    async def clear_conversation_history(self, user: User, clear_memory: bool = False):
        """Clear user's conversation history (keep profile and subscription)"""
        
        # Close all active conversations
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user.id, Conversation.is_active == True)
        )
        conversations = result.scalars().all()
        
        for conv in conversations:
            await self.close_conversation(conv)
        
        # Clear memory if requested
        if clear_memory:
            await self.memory_service.clear_user_memory(user.id, keep_anchors=False)
        else:
            # Just clear cache but keep long-term anchors
            await self.cache.clear_conversation_cache(user.id)
    
    async def get_enhanced_conversation_context(self, user: User, current_messages: List[Dict]) -> Dict:
        """Get enhanced conversation context with long-term memory"""
        return await self.memory_service.get_conversation_context(user.id, current_messages)
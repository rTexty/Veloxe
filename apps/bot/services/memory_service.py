import uuid
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import List, Dict, Optional
import sys
sys.path.append('../../../')

from shared.models.memory import MemoryAnchor, ConversationSummary
from shared.models.conversation import Conversation, Message
from shared.models.user import User
from shared.config.redis import RedisCache
from .gpt_service import GPTService


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.cache = RedisCache()
        self.gpt = GPTService()
    
    async def create_conversation_summary(self, conversation: Conversation) -> ConversationSummary:
        """Create summary of completed conversation"""
        
        # Get all messages from conversation
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        
        if not messages:
            return None
        
        # Build conversation text for GPT analysis
        conversation_text = ""
        for msg in messages:
            role = "Пользователь" if msg.role == "user" else "Бот"
            conversation_text += f"{role}: {msg.content}\n"
        
        # Ask GPT to summarize
        summary_prompt = f"""Проанализируй этот диалог с пользователем и создай структурированное резюме:

{conversation_text}

Верни JSON с полями:
- summary: краткое описание основного содержания диалога (2-3 предложения)
- main_topics: список главных тем, которые обсуждались
- emotional_state: эмоциональное состояние пользователя (одним словом)
- key_outcomes: важные выводы, решения или договорённости из диалога
- potential_anchors: список потенциальных долгосрочных якорей памяти (важные инсайты для будущих диалогов)

Отвечай только JSON, без дополнительного текста."""

        try:
            response = await self.gpt.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": summary_prompt}],
                max_tokens=800,
                temperature=0.3
            )
            
            import json
            summary_data = json.loads(response.choices[0].message.content)
            
            # Create summary record
            summary = ConversationSummary(
                user_id=conversation.user_id,
                conversation_id=conversation.id,
                summary=summary_data.get("summary", ""),
                main_topics=summary_data.get("main_topics", []),
                emotional_state=summary_data.get("emotional_state"),
                key_outcomes=summary_data.get("key_outcomes", []),
                message_count=len(messages),
                duration_minutes=int((messages[-1].created_at - messages[0].created_at).total_seconds() / 60) if len(messages) > 1 else 0
            )
            
            self.session.add(summary)
            await self.session.commit()
            
            # Process potential anchors
            if summary_data.get("potential_anchors"):
                await self._create_memory_anchors(
                    conversation.user_id,
                    summary_data["potential_anchors"],
                    conversation.session_id
                )
            
            return summary
            
        except Exception as e:
            print(f"Error creating conversation summary: {e}")
            return None
    
    async def _create_memory_anchors(self, user_id: int, potential_anchors: List[str], session_id: str):
        """Create memory anchors from potential anchors list"""
        
        for anchor_text in potential_anchors:
            if len(anchor_text.strip()) < 10:  # Skip too short anchors
                continue
            
            # Generate anchor ID
            anchor_id = str(uuid.uuid4())[:8]
            
            # Determine topic from anchor text (simple approach)
            topic = "general"
            topic_keywords = {
                "work": ["работа", "начальник", "коллеги", "офис", "проект"],
                "relationships": ["отношения", "партнер", "любовь", "романтика", "ссора"],
                "family": ["семья", "родители", "дети", "родственники"],
                "health": ["здоровье", "болезнь", "врач", "лечение", "самочувствие"],
                "emotions": ["эмоции", "чувства", "тревога", "грусть", "радость"]
            }
            
            anchor_lower = anchor_text.lower()
            for topic_name, keywords in topic_keywords.items():
                if any(keyword in anchor_lower for keyword in keywords):
                    topic = topic_name
                    break
            
            # Create anchor in database
            anchor = MemoryAnchor(
                user_id=user_id,
                anchor_id=anchor_id,
                topic=topic,
                insight=anchor_text,
                context=f"Из сессии {session_id}",
                source_session_id=session_id,
                auto_generated=True
            )
            
            self.session.add(anchor)
            
            # Cache in Redis
            await self.cache.set_memory_anchor(
                user_id,
                anchor_id,
                {
                    "topic": topic,
                    "insight": anchor_text,
                    "created_at": datetime.utcnow().isoformat(),
                    "strength": 1,
                    "auto_generated": True
                }
            )
        
        await self.session.commit()
    
    async def get_relevant_anchors(self, user_id: int, current_context: str, limit: int = 5) -> List[Dict]:
        """Get relevant memory anchors based on current conversation context"""
        
        # First try Redis cache
        cached_anchors = await self.cache.get_memory_anchors(user_id)
        
        if cached_anchors:
            # Simple relevance scoring based on keyword matching
            scored_anchors = []
            context_lower = current_context.lower()
            
            for anchor_id, anchor_data in cached_anchors.items():
                score = 0
                insight_lower = anchor_data["insight"].lower()
                
                # Topic matching
                if anchor_data["topic"] in context_lower:
                    score += 3
                
                # Keyword matching
                common_words = set(context_lower.split()) & set(insight_lower.split())
                score += len(common_words)
                
                # Strength bonus
                score += anchor_data.get("strength", 1)
                
                if score > 2:  # Only include relevant anchors
                    scored_anchors.append((score, anchor_data))
            
            # Sort by score and return top results
            scored_anchors.sort(reverse=True, key=lambda x: x[0])
            return [anchor for _, anchor in scored_anchors[:limit]]
        
        # Fallback to database
        result = await self.session.execute(
            select(MemoryAnchor)
            .where(and_(
                MemoryAnchor.user_id == user_id,
                MemoryAnchor.is_active == True
            ))
            .order_by(desc(MemoryAnchor.strength), desc(MemoryAnchor.last_referenced))
            .limit(limit)
        )
        
        anchors = result.scalars().all()
        return [
            {
                "topic": anchor.topic,
                "insight": anchor.insight,
                "strength": anchor.strength,
                "created_at": anchor.created_at.isoformat()
            }
            for anchor in anchors
        ]
    
    async def reference_anchor(self, user_id: int, anchor_id: str):
        """Mark anchor as referenced (increase strength)"""
        
        # Update in database
        result = await self.session.execute(
            select(MemoryAnchor)
            .where(and_(
                MemoryAnchor.user_id == user_id,
                MemoryAnchor.anchor_id == anchor_id,
                MemoryAnchor.is_active == True
            ))
        )
        anchor = result.scalar_one_or_none()
        
        if anchor:
            anchor.strength += 1
            anchor.last_referenced = datetime.utcnow()
            await self.session.commit()
            
            # Update Redis cache
            cached_anchors = await self.cache.get_memory_anchors(user_id)
            if anchor_id in cached_anchors:
                cached_anchors[anchor_id]["strength"] = anchor.strength
                await self.cache.set_memory_anchor(
                    user_id,
                    anchor_id,
                    cached_anchors[anchor_id]
                )
    
    async def get_conversation_context(self, user_id: int, current_messages: List[Dict]) -> Dict:
        """Get full conversation context including cache and long-term memory"""
        
        # Get cached recent context
        cached_context = await self.cache.get_conversation_cache(user_id)
        
        # Build current context string for anchor matching
        recent_text = " ".join([msg["content"] for msg in current_messages[-5:]])
        
        # Get relevant memory anchors
        relevant_anchors = await self.get_relevant_anchors(user_id, recent_text)
        
        # Combine everything
        context = {
            "recent_messages": current_messages,
            "cached_context": cached_context,
            "memory_anchors": relevant_anchors,
            "long_memory_active": len(relevant_anchors) > 0
        }
        
        # Cache current context
        await self.cache.set_conversation_cache(user_id, {
            "last_update": datetime.utcnow().isoformat(),
            "message_count": len(current_messages),
            "recent_topics": recent_text[:200]  # First 200 chars
        })
        
        return context
    
    async def clear_user_memory(self, user_id: int, keep_anchors: bool = True):
        """Clear user memory (for privacy/reset)"""
        
        # Clear Redis cache
        await self.cache.clear_conversation_cache(user_id)
        
        if not keep_anchors:
            # Clear long-term anchors
            result = await self.session.execute(
                select(MemoryAnchor).where(MemoryAnchor.user_id == user_id)
            )
            anchors = result.scalars().all()
            
            for anchor in anchors:
                anchor.is_active = False
                await self.cache.delete_memory_anchor(user_id, anchor.anchor_id)
            
            await self.session.commit()
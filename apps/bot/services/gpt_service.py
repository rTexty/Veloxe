import asyncio
import re
from openai import AsyncOpenAI
from typing import List, Dict, Optional
import sys
sys.path.append('../../../')

from shared.config.settings import settings


class GPTService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def generate_response(
        self, 
        user_message: str, 
        user_profile: Dict, 
        conversation_history: List[Dict],
        settings_dict: Dict,
        bot=None,
        chat_id=None
    ) -> Dict:
        """
        Generate empathetic response using GPT
        Returns: {
            'response': str,
            'is_crisis': bool,
            'blocks': List[str],
            'token_count': int
        }
        """
        
        # Check for crisis keywords first
        is_crisis = await self._detect_crisis(user_message, settings_dict)
        
        if is_crisis:
            crisis_response = await self._get_crisis_response(settings_dict)
            return {
                'response': crisis_response,
                'is_crisis': True,
                'blocks': [crisis_response],
                'token_count': 0
            }
        
        # Build system prompt
        system_prompt = await self._build_system_prompt(user_profile, settings_dict)
        
        # Build messages for GPT
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (last N messages)
        memory_window = settings_dict.get('memory_window_size', 15)
        recent_history = conversation_history[-memory_window:] if conversation_history else []
        
        for msg in recent_history:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Start continuous typing indicator if bot provided
            typing_task = None
            if bot and chat_id:
                typing_task = asyncio.create_task(self._maintain_typing(bot, chat_id))
            
            try:
                # Call OpenAI API
                response = await self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    max_tokens=1000,  # Restored full response length
                    temperature=0.8
                )
            finally:
                # Stop typing indicator
                if typing_task:
                    typing_task.cancel()
                    try:
                        await typing_task
                    except asyncio.CancelledError:
                        pass
            
            response_text = response.choices[0].message.content
            token_count = response.usage.total_tokens
            
            # Process response into blocks
            blocks = self._process_response_blocks(response_text, settings_dict)
            
            return {
                'response': response_text,
                'is_crisis': False,
                'blocks': blocks,
                'token_count': token_count
            }
            
        except Exception as e:
            # Fallback response
            return {
                'response': "Кажется, я задумался... Попробуем ещё раз?",
                'is_crisis': False,
                'blocks': ["Кажется, я задумался... Попробуем ещё раз?"],
                'token_count': 0,
                'error': str(e)
            }
    
    async def _detect_crisis(self, text: str, settings_dict: Dict) -> bool:
        """Detect crisis keywords in user message"""
        # Get crisis keywords from settings
        from services.settings_service import SettingsService
        from shared.config.database import async_session
        
        async with async_session() as session:
            settings_service = SettingsService(session)
            
            crisis_keywords = await settings_service.get_setting("crisis_keywords", [
                "умереть", "умру", "суицид", "покончить", "повеситься", 
                "убить себя", "не хочу жить", "нет смысла жить", "конец",
                "прыгнуть с крыши", "таблетки", "смерть", "убийство себя",
                "повешусь", "отравлюсь", "утоплюсь", "зарежусь", "застрелюсь"
            ])
        
        text_lower = text.lower()
        
        # Check for exact phrases and word boundaries
        for keyword in crisis_keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    async def _get_crisis_response(self, settings_dict: Dict) -> str:
        """Return crisis intervention response"""
        from services.settings_service import SettingsService
        from shared.config.database import async_session
        
        async with async_session() as session:
            settings_service = SettingsService(session)
            
            crisis_response = await settings_service.get_setting("crisis_response_text", 
                "Мне очень жаль, что тебе так тяжело. Я не могу заменить живого специалиста, "
                "но хочу, чтобы ты сейчас получил помощь.\n\n"
                "🆘 Горячая линия: 8 800 2000 122\n"
                "📞 Экстренные службы: 112"
            )
            
        return crisis_response
    
    async def _build_system_prompt(self, user_profile: Dict, settings_dict: Dict) -> str:
        """Build system prompt based on user profile"""
        
        # Get system prompt from settings
        from services.settings_service import SettingsService
        from shared.config.database import async_session
        
        async with async_session() as session:
            settings_service = SettingsService(session)
            
            base_prompt = await settings_service.get_setting(
                "system_prompt",
                """Ты эмпатичный помощник для эмоциональной поддержки. 

ВАЖНЫЕ ПРАВИЛА:
- НЕ давай конкретных советов или медицинских рекомендаций
- НЕ используй слово "вы", только "ты"
- НЕ упоминай GPT/AI или что ты робот
- НЕ выпрашивай доверие фразами типа "я здесь для тебя"
- НЕ морализируй и не читай лекции
- Мат и агрессию интерпретируй как выражение эмоций

ЧТО ДЕЛАТЬ:
- Фокусируйся на эмоциях и поддержке
- Говори от сердца, человечно
- Задавай открытые вопросы о чувствах
- Отражай эмоции пользователя
- Будь кратким но теплым"""
            )

        # Add user context if available
        if user_profile:
            context = "\n\nКОНТЕКСТ ПОЛЬЗОВАТЕЛЯ:\n"
            if user_profile.get('name'):
                context += f"Имя: {user_profile['name']}\n"
            if user_profile.get('age'):
                context += f"Возраст: {user_profile['age']}\n"
            if user_profile.get('emotion_tags'):
                emotions = ', '.join(user_profile['emotion_tags'])
                context += f"Частые эмоции: {emotions}\n"
            if user_profile.get('topic_tags'):
                topics = ', '.join(user_profile['topic_tags'])
                context += f"Волнующие темы: {topics}\n"
            
            # Add long-term memory anchors if available
            if user_profile.get('memory_anchors'):
                context += f"\nВАЖНЫЕ ВОСПОМИНАНИЯ ИЗ ПРОШЛЫХ РАЗГОВОРОВ:\n"
                for anchor in user_profile['memory_anchors'][:3]:  # Max 3 anchors
                    context += f"• {anchor['insight']}\n"
                context += "\nМожешь ссылаться на эти моменты, если они связаны с текущей темой.\n"
            
            base_prompt += context
        
        return base_prompt
    
    def _process_response_blocks(self, response: str, settings_dict: Dict) -> List[str]:
        """Split response into blocks for natural delivery"""
        
        # Split by double newlines
        blocks = response.split('\n\n')
        
        # Remove empty blocks
        blocks = [block.strip() for block in blocks if block.strip()]
        
        # Merge short blocks (less than 30 chars)
        min_block_length = settings_dict.get('min_block_length', 30)
        merged_blocks = []
        current_block = ""
        
        for block in blocks:
            if len(current_block + block) < min_block_length:
                current_block += " " + block if current_block else block
            else:
                if current_block:
                    merged_blocks.append(current_block)
                current_block = block
        
        if current_block:
            merged_blocks.append(current_block)
        
        # Limit max blocks
        max_blocks = settings_dict.get('max_blocks_per_reply', 3)
        if len(merged_blocks) > max_blocks:
            # Merge tail blocks
            tail = " ".join(merged_blocks[max_blocks-1:])
            merged_blocks = merged_blocks[:max_blocks-1] + [tail]
        
        return merged_blocks or [response]  # Fallback to original if processing fails
    
    async def _maintain_typing(self, bot, chat_id):
        """Maintain typing indicator during GPT processing"""
        try:
            while True:
                await bot.send_chat_action(chat_id, "typing")
                await asyncio.sleep(4)  # Typing indicator lasts ~5 seconds, refresh every 4
        except asyncio.CancelledError:
            # Task was cancelled, stop typing
            pass
        except Exception:
            # Ignore typing errors
            pass
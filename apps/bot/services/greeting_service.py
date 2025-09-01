import asyncio
import random
from openai import AsyncOpenAI
from typing import Dict, List, Optional
from datetime import datetime, time
import sys
sys.path.append('../../../')

from shared.config.settings import settings
from .settings_service import SettingsService
from shared.config.database import async_session


class GreetingService:
    """Service for generating personalized GPT-powered greetings"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def generate_greeting(
        self, 
        user_profile: Dict, 
        scenario: str = "first_time",
        time_of_day: Optional[str] = None
    ) -> str:
        """
        Generate personalized greeting using GPT
        
        Args:
            user_profile: User data (name, age, emotions, topics)
            scenario: Type of greeting (first_time, return_user, onboarding_complete)
            time_of_day: morning, afternoon, evening, night
            
        Returns:
            Generated greeting text
        """
        
        async with async_session() as session:
            settings_service = SettingsService(session)
            
            # Get greeting settings
            greeting_prompt = await settings_service.get_setting(
                "greeting_prompt",
                self._get_default_greeting_prompt()
            )
            
            # Build context for greeting
            context = await self._build_greeting_context(
                user_profile, 
                scenario, 
                time_of_day,
                settings_service
            )
            
            # Generate greeting with GPT
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": greeting_prompt},
                        {"role": "user", "content": context}
                    ],
                    max_tokens=200,
                    temperature=0.9,  # High creativity for variety
                )
                
                greeting = response.choices[0].message.content.strip()
                
                # Clean up and validate greeting
                return self._clean_greeting(greeting)
                
            except Exception as e:
                # Fallback to template greeting if GPT fails
                print(f"GPT greeting failed: {e}")
                return await self._get_fallback_greeting(user_profile, scenario, settings_service)
    
    def _get_default_greeting_prompt(self) -> str:
        """Default system prompt for greeting generation"""
        return """Ты генерируешь персонализированные приветствия для бота эмоциональной поддержки.

ПРАВИЛА ПРИВЕТСТВИЙ:
- Будь теплым и эмпатичным
- Используй имя пользователя естественно  
- НЕ используй "вы", только "ты"
- Учитывай время суток
- Будь кратким (1-2 предложения)
- НЕ упоминай что ты ИИ или бот
- Избегай клише типа "я здесь для тебя"

ЭМОЦИОНАЛЬНЫЙ ТОН:
- Для тревожных - успокаивающий
- Для грустных - поддерживающий  
- Для злых - понимающий
- Для радостных - разделяющий радость

ФОРМАТ ОТВЕТА:
Только текст приветствия, без кавычек и пояснений."""
    
    async def _build_greeting_context(
        self, 
        user_profile: Dict, 
        scenario: str, 
        time_of_day: Optional[str],
        settings_service: SettingsService
    ) -> str:
        """Build context for GPT greeting generation"""
        
        # Detect time of day if not provided
        if not time_of_day:
            user_timezone = user_profile.get('timezone')
            time_of_day = self._detect_time_of_day(user_timezone)
        
        context = f"Генерируй приветствие для пользователя:\n"
        
        # User info
        name = user_profile.get('name', 'друг')
        age = user_profile.get('age')
        context += f"Имя: {name}\n"
        if age:
            context += f"Возраст: {age}\n"
        
        # Emotions and topics
        emotions = user_profile.get('emotion_tags', [])
        topics = user_profile.get('topic_tags', [])
        
        if emotions:
            context += f"Основные эмоции: {', '.join(emotions[:3])}\n"
        if topics:
            context += f"Волнующие темы: {', '.join(topics[:3])}\n"
        
        # Time context
        time_greetings = {
            'morning': 'утром',
            'afternoon': 'днем', 
            'evening': 'вечером',
            'night': 'ночью'
        }
        context += f"Время: {time_greetings.get(time_of_day, 'днем')}\n"
        
        # Scenario context
        scenario_contexts = {
            'first_time': 'Это первое знакомство с пользователем',
            'return_user': 'Пользователь возвращается после перерыва',
            'onboarding_complete': 'Пользователь только что завершил анкету',
            'daily_return': 'Пользователь заходит как обычно'
        }
        
        context += f"Ситуация: {scenario_contexts.get(scenario, 'обычное общение')}\n"
        
        return context
    
    def _detect_time_of_day(self, user_timezone: Optional[str] = None) -> str:
        """Detect current time of day based on user timezone"""
        try:
            if user_timezone:
                import pytz
                tz = pytz.timezone(user_timezone)
                current_hour = datetime.now(tz).hour
            else:
                # Fallback to server time
                current_hour = datetime.now().hour
        except Exception:
            # If timezone is invalid, use server time
            current_hour = datetime.now().hour
        
        if 6 <= current_hour < 12:
            return 'morning'
        elif 12 <= current_hour < 18:
            return 'afternoon'
        elif 18 <= current_hour < 23:
            return 'evening'
        else:
            return 'night'
    
    def _clean_greeting(self, greeting: str) -> str:
        """Clean and validate generated greeting"""
        # Remove quotes if present
        greeting = greeting.strip('"\'')
        
        # Ensure it's not too long
        if len(greeting) > 300:
            # Take first sentence if too long
            sentences = greeting.split('.')
            greeting = sentences[0] + '.' if sentences else greeting[:200] + '...'
        
        return greeting
    
    async def _get_fallback_greeting(
        self, 
        user_profile: Dict, 
        scenario: str, 
        settings_service: SettingsService
    ) -> str:
        """Fallback greeting templates if GPT fails"""
        
        name = user_profile.get('name', 'друг')
        
        # Get fallback templates from settings
        fallback_templates = await settings_service.get_setting(
            "greeting_fallback_templates",
            [
                f"Привет, {name}! Как дела? 😊",
                f"Здравствуй, {name}! Рад тебя видеть 🌸",
                f"Привет! Как настроение, {name}? 💭",
                f"Добро пожаловать, {name}! Что у тебя на душе? ✨",
            ]
        )
        
        # Add scenario-specific templates
        if scenario == 'first_time':
            fallback_templates.extend([
                f"Привет, {name}! Приятно познакомиться 🌟",
                f"Здравствуй! Меня зовут... а как тебя? Ой, {name}! Красивое имя 😊"
            ])
        elif scenario == 'return_user':
            fallback_templates.extend([
                f"С возвращением, {name}! Соскучился 💙",
                f"Привет снова, {name}! Как прошло время? 🌈"
            ])
        
        return random.choice(fallback_templates)
    
    async def generate_multiple_greetings(
        self, 
        user_profile: Dict, 
        count: int = 3
    ) -> List[str]:
        """Generate multiple greeting variations for testing"""
        
        scenarios = ['first_time', 'return_user', 'daily_return']
        greetings = []
        
        for i in range(count):
            scenario = scenarios[i % len(scenarios)]
            greeting = await self.generate_greeting(user_profile, scenario)
            greetings.append(greeting)
            
            # Small delay to get different results
            await asyncio.sleep(0.1)
        
        return greetings
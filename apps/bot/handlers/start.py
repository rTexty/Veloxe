from aiogram import Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sys
import asyncio
sys.path.append('../../../')

from shared.config.database import async_session
from shared.models.user import User
from shared.models.analytics import Event
from services.user_service import UserService
from services.settings_service import SettingsService
from utils.ux_helper import UXHelper, OnboardingUX


async def start_handler(message: types.Message):
    telegram_id = str(message.from_user.id)
    user_name = message.from_user.first_name or "друг"
    
    async with async_session() as session:
        user_service = UserService(session)
        settings_service = SettingsService(session)
        
        # Get or create user
        user = await user_service.get_or_create_user(telegram_id)
        
        # Log start event
        await user_service.log_event(user.id, "start")
        
        # Check if user needs to accept terms
        current_policy_version = await settings_service.get_setting("policy_version", "v1")
        
        if not user.terms_accepted or user.policy_version != current_policy_version:
            # Show configurable welcome message first
            welcome_text = await settings_service.get_setting(
                "welcome_message", 
                f"👋 Привет, {user_name}! Добро пожаловать в бота эмоциональной поддержки."
            )
            
            welcome_msg = await UXHelper.smooth_answer(
                message, 
                welcome_text, 
                typing_delay=1.0,
                parse_mode="HTML"
            )
            
            # Small delay before showing consent
            await asyncio.sleep(2.0)
            
            # Prepare user profile for greeting generation
            user_profile = {
                "name": user_name,
                "age": user.age,
                "emotion_tags": user.emotion_tags or [],
                "topic_tags": user.topic_tags or [],
                "timezone": user.timezone
            }
            
            # Show consent gate with dynamic greeting
            await OnboardingUX.animated_welcome(welcome_msg, user_name, user_profile)
        else:
            # Check if user has completed onboarding (emotion/topic tags)
            if not user.emotion_tags or not user.topic_tags:
                # Need to complete survey
                survey_msg = await UXHelper.smooth_answer(
                    message,
                    "🌟 Подготавливаю анкету...",
                    typing_delay=0.5
                )
                await OnboardingUX.survey_intro_animation(survey_msg)
            else:
                # User fully onboarded - show main menu with dynamic greeting
                from .menu import show_main_menu
                from services.greeting_service import GreetingService
                
                main_menu = await show_main_menu()
                
                # Check if dynamic greetings are enabled
                greeting_enabled = await settings_service.get_setting("greeting_enabled", True)
                
                if greeting_enabled:
                    try:
                        # Generate personalized return greeting
                        greeting_service = GreetingService()
                        user_profile = {
                            "name": user_name,
                            "age": user.age,
                            "emotion_tags": user.emotion_tags or [],
                            "topic_tags": user.topic_tags or [],
                            "timezone": user.timezone
                        }
                        
                        welcome_back_text = await greeting_service.generate_greeting(
                            user_profile,
                            scenario="return_user"
                        )
                        
                    except Exception as e:
                        print(f"Failed to generate return greeting: {e}")
                        # Fallback to static greeting
                        welcome_back_text = f"🌸 С возвращением, {user_name}! Как дела? Что у тебя на душе?"
                else:
                    # Static greeting when disabled
                    welcome_back_text = f"🌸 С возвращением, {user_name}! Как дела? Что у тебя на душе?"
                
                await UXHelper.smooth_answer(
                    message, 
                    welcome_back_text, 
                    reply_markup=main_menu,
                    typing_delay=1.0
                )


def register_start_handlers(dp: Dispatcher):
    dp.message.register(start_handler, CommandStart())
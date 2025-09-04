from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import sys
sys.path.append('../../../')

from handlers.survey import SurveyStates
from utils.ux_helper import UXHelper


class SurveyMiddleware(BaseMiddleware):
    """Middleware to protect survey flow from interruptions"""
    
    def __init__(self):
        super().__init__()
        # Commands allowed during survey states
        self.survey_allowed_commands = {
            '/start',  # Always allow restart
            'consent_accept', 'consent_decline',  # Consent flow
        }
        
        # Survey-specific callback data patterns that are allowed
        self.survey_allowed_callbacks = {
            'survey_name', 'survey_age', 'survey_gender', 'survey_city',
            'gender_male', 'gender_female', 'gender_not_applicable',
            'survey_confirm', 'survey_edit'
        }
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Get FSM context
        state_context: FSMContext = data.get("state")
        if not state_context:
            return await handler(event, data)
        
        # Check if user is in survey state
        current_state = await state_context.get_state()
        if not current_state or not current_state.startswith("SurveyStates:"):
            return await handler(event, data)
        
        # User is in survey - check if action is allowed
        is_allowed = False
        
        if isinstance(event, Message):
            # Allow text input for specific survey states
            if current_state in ["SurveyStates:waiting_name", "SurveyStates:waiting_age", "SurveyStates:waiting_city"]:
                is_allowed = True
            # Allow specific commands
            elif event.text and event.text in self.survey_allowed_commands:
                is_allowed = True
                
        elif isinstance(event, CallbackQuery):
            # Allow survey-specific callbacks
            if event.data in self.survey_allowed_callbacks:
                is_allowed = True
            # Allow emotion/topic selection callbacks
            elif (event.data.startswith(('emotion_', 'topic_')) or 
                  event.data.endswith('_done')):
                is_allowed = True
        
        if not is_allowed:
            # Block non-survey actions with friendly message
            block_text = "📝 <b>Давайте сначала завершим анкету!</b>\n\nВы сейчас заполняете профиль. Пожалуйста, ответьте на текущий вопрос или нажмите /start для начала сначала."
            
            if isinstance(event, Message):
                await UXHelper.smooth_answer(
                    event,
                    block_text,
                    typing_delay=0.2
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "📝 Сначала завершите анкету!",
                    show_alert=True
                )
            
            return  # Block further processing
        
        # Action is allowed - proceed normally
        return await handler(event, data)
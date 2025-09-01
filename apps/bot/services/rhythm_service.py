import asyncio
import random
from typing import List
from aiogram import types
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from services.settings_service import SettingsService
from utils.ux_helper import UXHelper


class RhythmService:
    """Service for delivering GPT responses with natural rhythm"""
    
    def __init__(self):
        pass
    
    async def send_blocks_with_rhythm(
        self, 
        message: types.Message, 
        blocks: List[str], 
        user_id: int,
        settings_dict: dict = None
    ) -> types.Message:
        """
        Send response blocks with natural rhythm and pauses
        
        Args:
            message: Original user message to reply to
            blocks: List of text blocks to send
            user_id: User ID for personalized settings
            
        Returns:
            Last sent message (for adding inline buttons)
        """
        if not blocks:
            return message
        
        # Use provided settings or get from database
        if settings_dict:
            delay_min = settings_dict.get("delay_between_blocks_min", 1500)
            delay_max = settings_dict.get("delay_between_blocks_max", 2500)
        else:
            # Fallback to database if settings not provided
            async with async_session() as session:
                settings_service = SettingsService(session)
                delay_min = await settings_service.get_setting("delay_between_blocks_min", 1500)
                delay_max = await settings_service.get_setting("delay_between_blocks_max", 2500)
            
        typing_duration_base = 0.5
        typing_duration_per_word = 0.05
        
        last_message = None
        
        for i, block in enumerate(blocks):
            # Calculate typing duration based on block length
            word_count = len(block.split())
            typing_duration = typing_duration_base + (word_count * typing_duration_per_word)
            typing_duration = min(typing_duration, 4.0)  # Max 5 seconds typing
            
            # Show typing action
            await message.bot.send_chat_action(message.chat.id, "typing")
            await asyncio.sleep(typing_duration)
            
            # Send the block
            if i == 0:
                # First block is a reply to user message
                last_message = await message.answer(
                    block,
                    parse_mode="HTML"
                )
            else:
                # Subsequent blocks are regular messages
                last_message = await message.answer(
                    block,
                    parse_mode="HTML"
                )
            
            # Add pause between blocks (except for last one)
            if i < len(blocks) - 1:
                pause_duration = random.uniform(delay_min / 1000, delay_max / 1000)
                await asyncio.sleep(pause_duration)
        
        # No buttons needed - clean conversation flow
        
        return last_message
    
    async def send_with_typing(
        self, 
        message: types.Message, 
        text: str,
        delay: float = None
    ) -> types.Message:
        """
        Send single message with typing simulation
        
        Args:
            message: Message to reply to
            text: Text to send
            delay: Custom typing delay (if None, calculated from text length)
            
        Returns:
            Sent message
        """
        if delay is None:
            # Calculate delay based on text length
            word_count = len(text.split())
            delay = 1.0 + (word_count * 0.08)  # ~0.08s per word
            delay = min(delay, 4.0)  # Max 4 seconds
        
        # Truncate message if it exceeds Telegram's 4096 character limit
        if len(text) > 4096:
            text = text[:4093] + "..."
        
        # Show typing
        await message.bot.send_chat_action(message.chat.id, "typing")
        await asyncio.sleep(delay)
        
        # Send message
        return await message.answer(text, parse_mode="HTML")
    
    async def send_error_with_retry(
        self, 
        message: types.Message, 
        error_text: str = None,
        retry_callback: str = "gpt_retry"
    ) -> types.Message:
        """
        Send error message with retry button
        
        Args:
            message: Message to reply to
            error_text: Custom error text
            retry_callback: Callback data for retry button
            
        Returns:
            Sent message with retry button
        """
        if error_text is None:
            error_text = "🤔 Кажется, я задумался... Попробуем ещё раз?"
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        retry_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Повторить", callback_data=retry_callback)]
        ])
        
        return await self.send_with_typing(
            message, 
            error_text, 
            delay=1.0
        )
    
    async def show_thinking_animation(
        self, 
        message: types.Message,
        steps: List[str] = None,
        final_callback = None
    ) -> types.Message:
        """
        Show thinking animation before generating response
        
        Args:
            message: Message to reply to
            steps: Custom thinking steps
            final_callback: Function to call after animation
            
        Returns:
            Message that can be edited with final response
        """
        if steps is None:
            steps = [
                "🤔 Обдумываю...",
                "💭 Анализирую ваши слова...", 
                "✨ Готовлю ответ..."
            ]
        
        # Send initial message
        thinking_msg = await message.answer(steps[0])
        
        # Animate through steps
        for i, step in enumerate(steps[1:], 1):
            await asyncio.sleep(0.8)
            try:
                await thinking_msg.edit_text(step)
            except Exception:
                pass  # Ignore if message can't be edited
        
        return thinking_msg
    
    async def _maintain_typing_indicator(self, bot, chat_id):
        """Maintain continuous typing indicator during long operations"""
        try:
            while True:
                await bot.send_chat_action(chat_id, "typing")
                await asyncio.sleep(4)  # Typing lasts ~5 seconds, refresh every 4
        except asyncio.CancelledError:
            pass  # Task was cancelled, stop typing
        except Exception:
            pass  # Ignore typing errors
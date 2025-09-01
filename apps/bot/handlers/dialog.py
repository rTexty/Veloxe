import asyncio
from aiogram import Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from services.user_service import UserService
from services.conversation_service import ConversationService
from services.gpt_service import GPTService
from services.rhythm_service import RhythmService
from services.settings_cache import settings_cache
from utils.ux_helper import UXHelper, OnboardingUX, AnimatedMessages


async def dialog_message_handler(message: types.Message):
    """Handle user messages in dialog"""
    telegram_id = str(message.from_user.id)
    
    async with async_session() as session:
        user_service = UserService(session)
        conv_service = ConversationService(session)
        gpt_service = GPTService()
        rhythm_service = RhythmService()
        
        # Get user
        user = await user_service.get_or_create_user(telegram_id)
        
        # Check if user completed onboarding
        if not user.terms_accepted or not user.name:
            onboarding_text = "🌟 <b>Давайте сначала знакомиться!</b>\n\nДля начала общения нужно завершить быструю регистрацию."
            keyboard = OnboardingUX.create_button_keyboard([
                ("🚀 Начать регистрацию", "start_onboarding")
            ])
            await UXHelper.smooth_answer(
                message, 
                onboarding_text, 
                reply_markup=keyboard,
                typing_delay=0.8
            )
            return
        
        # Show typing indicator IMMEDIATELY after receiving message
        await message.bot.send_chat_action(message.chat.id, "typing")
        
        # Check if user can send messages
        limit_check = await conv_service.can_user_send_message(user)
        
        if not limit_check['can_send']:
            await show_paywall(message, limit_check)
            return
        
        try:
            # Start continuous typing task for long operations
            typing_task = asyncio.create_task(
                rhythm_service._maintain_typing_indicator(message.bot, message.chat.id)
            )
            
            # Load settings from Redis cache (much faster than 6 DB queries)
            settings_dict = await settings_cache.get_bot_settings()
            
            # Execute database operations efficiently
            conversation = await conv_service.get_or_create_active_conversation(user)
            await conv_service.add_message(conversation, "user", message.text or "")
            history = await conv_service.get_conversation_history(conversation)
            
            # Get memory context if enabled
            if settings_dict['long_memory_enabled']:
                enhanced_context = await conv_service.get_enhanced_conversation_context(user, history)
                memory_anchors = enhanced_context.get('memory_anchors', [])
            else:
                memory_anchors = []
            
            # Prepare user profile for GPT
            user_profile = {
                'name': user.name,
                'age': user.age,
                'gender': user.gender,
                'emotion_tags': user.emotion_tags or [],
                'topic_tags': user.topic_tags or [],
                'memory_anchors': memory_anchors
            }
            
            # Stop the continuous typing task before GPT call (GPT service has its own typing)
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass
            
            # Generate response with continued typing
            gpt_response = await gpt_service.generate_response(
                message.text or "",
                user_profile,
                history,
                settings_dict,
                bot=message.bot,
                chat_id=message.chat.id
            )
            
            # Handle crisis response
            if gpt_response['is_crisis']:
                await handle_crisis_response(message, user, user_service, conv_service, conversation)
                return
            
            # Consume daily message (only for non-subscribers)
            await conv_service.consume_daily_message(user)
            
            # Add assistant message to conversation
            await conv_service.add_message(
                conversation, 
                "assistant", 
                gpt_response['response'],
                gpt_response['token_count']
            )
            
            # Send response with beautiful rhythm (pass settings to avoid DB calls)
            await rhythm_service.send_blocks_with_rhythm(
                message, 
                gpt_response['blocks'], 
                user.id,  # type: ignore
                settings_dict  # Pass settings to avoid additional DB queries
            )
            print(f"[DEBUG] GPT response sent, checking limit warning: remaining={limit_check.get('remaining')}")
            
            # Log message event
            await user_service.log_event(
                user.id,  # type: ignore 
                "message_out",
                {
                    'token_count': gpt_response['token_count'],
                    'blocks_count': len(gpt_response['blocks'])
                }
            )
            
            # Show remaining daily messages warning AFTER sending response
            print(f"[DEBUG] Checking warning: reason={limit_check.get('reason')}, remaining={limit_check.get('remaining')}")
            if limit_check['reason'] == 'daily_free_limit' and limit_check['remaining'] <= 2:
                # Update remaining count after consumption
                remaining_after = limit_check['remaining'] - 1
                print(f"[DEBUG] Showing warning: remaining_after={remaining_after}")
                if remaining_after > 0:
                    warning_text = f"⏰ <b>Внимание!</b>\n\nОсталось <b>{remaining_after}</b> бесплатных сообщений на сегодня"
                    await UXHelper.smooth_answer(
                        message, 
                        warning_text,
                        typing_delay=0.5
                    )
            
        except Exception as e:
            # Beautiful error handling with RhythmService
            await rhythm_service.send_error_with_retry(
                message,
                "😔 <b>Упс! Что-то пошло не так</b>\n\nКажется, я слишком глубоко задумался... Попробуйте ещё раз?",
                "retry_dialog"
            )
            print(f"Dialog error: {e}")


async def send_response_blocks(message: types.Message, blocks: list, settings_dict: dict):
    """Send response blocks with natural delays and beautiful UX"""
    
    delay_min = settings_dict['delay_between_blocks_min'] / 1000  # Convert to seconds
    delay_max = settings_dict['delay_between_blocks_max'] / 1000
    
    for i, block in enumerate(blocks):
        if i > 0:  # No delay before first block
            # Random delay between blocks
            import random
            delay = random.uniform(delay_min, delay_max)
            await asyncio.sleep(delay)
        
        # Show typing action with UX helper
        await UXHelper.typing_action(message.chat.id, message.bot, duration=1.0)
        
        # No action buttons needed
        keyboard = None
        
        await message.answer(block, reply_markup=keyboard, parse_mode="HTML")


async def show_paywall(message: types.Message, limit_check: dict):
    """Show beautiful subscription paywall"""
    
    if limit_check['reason'] == 'daily_limit_exceeded':
        text = f"🚫 <b>Дневной лимит исчерпан</b>\n\n"
        text += f"Использовано: <b>{limit_check['used']}/{limit_check['limit']}</b> сообщений\n\n"
        text += "🌅 Лимит обновится завтра\n"
        text += "✨ Или подключите подписку для неограниченного общения"
    else:
        text = "🔒 <b>Нужна подписка</b>\n\nДля продолжения общения необходима подписка"
    
    keyboard = OnboardingUX.create_button_keyboard([
        ("💳 Подключить подписку", "show_subscription")
    ])
    
    await UXHelper.smooth_answer(
        message, 
        text, 
        reply_markup=keyboard,
        typing_delay=1.0
    )


async def handle_crisis_response(message, user, user_service, conv_service, conversation):
    """Handle crisis situation with enhanced UX"""
    from datetime import datetime, timedelta
    from shared.models.crisis import CrisisEvent
    
    # Set user in crisis mode with freeze timer
    user.is_in_crisis = True
    user.crisis_freeze_until = datetime.utcnow() + timedelta(hours=12)  # 12-hour freeze
    
    await user_service.session.commit()
    
    # Create crisis event record
    crisis_event = CrisisEvent(
        user_id=user.id,
        trigger_words=message.text[:200],  # Store first 200 chars of trigger message
        severity="HIGH",
        is_resolved=False,
        safety_contacts_shown=False,
        user_confirmed_safety=False
    )
    user_service.session.add(crisis_event)
    
    # Log crisis event
    await user_service.log_event(user.id, "crisis_triggered")
    
    # Add crisis message to conversation
    await conv_service.add_message(conversation, "assistant", "CRISIS_RESPONSE", is_crisis_related=True)
    
    # Show empathetic crisis response with safety buttons
    crisis_text = (
        "🤗 <b>Я очень переживаю за тебя</b>\n\n"
        "Мне жаль, что тебе сейчас так тяжело. Я не могу заменить живого специалиста, но хочу, чтобы ты получил помощь прямо сейчас.\n\n"
        "🆘 <b>В экстренных случаях звони: 112</b>"
    )
    
    keyboard = OnboardingUX.create_button_keyboard([
        ("🆘 Найти помощь рядом", "show_crisis_help"),
        ("✅ Я в безопасности", "crisis_safe")
    ], rows=2)
    
    await UXHelper.smooth_answer(
        message, 
        crisis_text, 
        reply_markup=keyboard,
        typing_delay=1.5
    )


# Button handlers removed for cleaner conversation flow


def register_dialog_handlers(dp: Dispatcher):
    # Regular message handler (lowest priority)
    dp.message.register(dialog_message_handler, F.text)
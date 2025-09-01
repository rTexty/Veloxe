from aiogram import Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from services.user_service import UserService
from services.settings_service import SettingsService
from utils.ux_helper import UXHelper, OnboardingUX, AnimatedMessages


class SurveyStates(StatesGroup):
    waiting_name = State()
    waiting_age = State()
    waiting_gender = State()
    waiting_city = State()
    waiting_emotions = State()
    waiting_topics = State()
    confirming = State()


async def survey_name_handler(callback: types.CallbackQuery, state: FSMContext):
    question_text = OnboardingUX.format_survey_question(
        "Как вас зовут?",
        1, 6,
        "Это поможет мне обращаться к вам по имени 😊"
    )
    
    await UXHelper.smooth_edit_text(
        callback.message,
        question_text,
        typing_delay=0.8
    )
    await state.set_state(SurveyStates.waiting_name)


async def name_input_handler(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    
    keyboard = OnboardingUX.create_button_keyboard([
        ("🎂 Указать возраст", "survey_age"),
        ("⏭️ Пропустить", "survey_gender")
    ])
    
    response_text = f"🌟 <b>Приятно познакомиться, {message.text}!</b>\n\nПродолжаем знакомство?"
    
    await UXHelper.smooth_answer(
        message, 
        response_text, 
        reply_markup=keyboard,
        typing_delay=1.0
    )


async def survey_age_handler(callback: types.CallbackQuery, state: FSMContext):
    question_text = OnboardingUX.format_survey_question(
        "Сколько вам лет?",
        2, 6,
        "Просто напишите число 🔢"
    )
    
    await UXHelper.smooth_edit_text(
        callback.message,
        question_text,
        typing_delay=0.6
    )
    await state.set_state(SurveyStates.waiting_age)


async def age_input_handler(message: types.Message, state: FSMContext):
    try:
        age = int(message.text)
        if 10 <= age <= 120:
            await state.update_data(age=age)
            await show_gender_selection(message)
        else:
            await UXHelper.smooth_answer(
                message,
                "🤔 Похоже, возраст необычный...\nПопробуйте ещё раз (10-120 лет)",
                typing_delay=0.5
            )
    except ValueError:
        await UXHelper.smooth_answer(
            message,
            "😅 Пожалуйста, напишите возраст просто цифрами",
            typing_delay=0.5
        )


async def survey_gender_handler(callback: types.CallbackQuery, state: FSMContext):
    await show_gender_selection(callback.message)


async def show_gender_selection(message: types.Message):
    question_text = OnboardingUX.format_survey_question(
        "Как к вам обращаться?",
        3, 6,
        "Можете пропустить, если не хотите указывать"
    )
    
    keyboard = OnboardingUX.create_button_keyboard([
        ("👨 Мужской", "gender_male"),
        ("👩 Женский", "gender_female"),
        ("🤷 Не важно", "gender_not_applicable"),
        ("⏭️ Пропустить", "survey_city")
    ], rows=2)
    
    await UXHelper.smooth_answer(
        message, 
        question_text, 
        reply_markup=keyboard,
        typing_delay=0.8
    )


async def gender_handler(callback: types.CallbackQuery, state: FSMContext):
    gender_map = {
        "gender_male": "male",
        "gender_female": "female", 
        "gender_not_applicable": "not_applicable"
    }
    
    await state.update_data(gender=gender_map[callback.data])
    
    question_text = OnboardingUX.format_survey_question(
        "Из какого вы города?",
        4, 6,
        "Это поможет мне учитывать ваш часовой пояс 🌍"
    )
    
    await UXHelper.smooth_edit_text(
        callback.message,
        question_text,
        typing_delay=0.6
    )
    await state.set_state(SurveyStates.waiting_city)


async def survey_city_handler(callback: types.CallbackQuery, state: FSMContext):
    question_text = OnboardingUX.format_survey_question(
        "Из какого вы города?",
        4, 6,
        "Это поможет мне учитывать ваш часовой пояс 🌍"
    )
    
    await UXHelper.smooth_edit_text(
        callback.message,
        question_text,
        typing_delay=0.6
    )
    await state.set_state(SurveyStates.waiting_city)


async def city_input_handler(message: types.Message, state: FSMContext):
    from utils.timezone_helper import TimezoneHelper
    
    city = message.text.strip()
    
    # Определяем часовой пояс с помощью улучшенной логики
    timezone = TimezoneHelper.get_timezone_from_city(city)
    if not timezone:
        timezone = "Europe/Moscow"  # Fallback to Moscow
    
    await state.update_data(city=city, timezone=timezone)
    
    # Transition message
    transition_text = f"🏙️ <b>{message.text}</b> — красивый город!\n\n⏭️ Переходим к следующему шагу..."
    transition_msg = await UXHelper.smooth_answer(
        message, 
        transition_text,
        typing_delay=1.0
    )
    
    await show_emotions_selection(transition_msg)


async def show_emotions_selection(message: types.Message):
    async with async_session() as session:
        settings_service = SettingsService(session)
        
        emotions = await settings_service.get_setting("emotion_tags", [
            "😰 тревога", "😥 чувство вины", "😡 злость", "😞 усталость",
            "😔 грусть", "😨 страх", "😤 раздражение", "😟 беспокойство"
        ])
    
    question_text = OnboardingUX.format_survey_question(
        "Какие эмоции часто с вами?",
        5, 6,
        "Выберите до 10 вариантов. Это поможет мне лучше понимать ваше состояние 💭"
    )
    
    keyboard = OnboardingUX.create_selection_keyboard(
        emotions, 
        "emotion",
        max_cols=2,
        done_text="✅ Продолжить"
    )
    
    await UXHelper.smooth_edit_text(
        message,
        question_text,
        reply_markup=keyboard,
        typing_delay=1.2
    )


async def emotion_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_emotions = data.get("selected_emotions", set())
    
    emotion_index = callback.data.replace("emotion_", "")
    
    if emotion_index in selected_emotions:
        selected_emotions.remove(emotion_index)
        await callback.answer(f"❌ Убрал. Выбрано: {len(selected_emotions)}")
    else:
        if len(selected_emotions) < 10:
            selected_emotions.add(emotion_index)
            await callback.answer(f"✅ Добавил! Выбрано: {len(selected_emotions)}")
        else:
            await callback.answer("Максимум 10 эмоций 😊")
    
    await state.update_data(selected_emotions=selected_emotions)
    
    # Update keyboard to show selections
    async with async_session() as session:
        settings_service = SettingsService(session)
        emotions = await settings_service.get_setting("emotion_tags", [
            "😰 тревога", "😥 чувство вины", "😡 злость", "😞 усталость",
            "😔 грусть", "😨 страх", "😤 раздражение", "😟 беспокойство"
        ])
    
    keyboard = OnboardingUX.create_selection_keyboard(
        emotions, 
        "emotion",
        selected_indices=selected_emotions,
        max_cols=2,
        done_text="✅ Продолжить"
    )
    
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass  # Ignore if message is the same


async def emotions_done_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_count = len(data.get("selected_emotions", set()))
    
    if selected_count == 0:
        await callback.answer("Выберите хотя бы одну эмоцию 😊")
        return
        
    # Nice transition
    transition_text = f"✨ Отлично! Выбрано {selected_count} эмоций\n\n⏭️ Последний шаг..."
    await UXHelper.smooth_edit_text(
        callback.message,
        transition_text,
        typing_delay=0.8
    )
    
    await show_topics_selection(callback.message)


async def show_topics_selection(message: types.Message):
    async with async_session() as session:
        settings_service = SettingsService(session)
        
        topics = await settings_service.get_setting("topic_tags", [
            "💼 работа", "❤️ отношения", "👨‍👩‍👧 семья", "🏥 здоровье",
            "💰 деньги", "🎓 учеба", "🤝 друзья", "🏠 быт"
        ])
    
    question_text = OnboardingUX.format_survey_question(
        "Какие темы вас волнуют?",
        6, 6,
        "Выберите до 8 тем, о которых хотели бы поговорить 💬"
    )
    
    keyboard = OnboardingUX.create_selection_keyboard(
        topics, 
        "topic",
        max_cols=2,
        done_text="🎉 Завершить анкету"
    )
    
    await UXHelper.smooth_edit_text(
        message,
        question_text,
        reply_markup=keyboard,
        typing_delay=1.0
    )


async def topic_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_topics = data.get("selected_topics", set())
    
    topic_index = callback.data.replace("topic_", "")
    
    if topic_index in selected_topics:
        selected_topics.remove(topic_index)
        await callback.answer(f"❌ Убрал. Выбрано: {len(selected_topics)}")
    else:
        if len(selected_topics) < 8:
            selected_topics.add(topic_index)
            await callback.answer(f"✅ Добавил! Выбрано: {len(selected_topics)}")
        else:
            await callback.answer("Максимум 8 тем 😊")
    
    await state.update_data(selected_topics=selected_topics)
    
    # Update keyboard to show selections
    async with async_session() as session:
        settings_service = SettingsService(session)
        topics = await settings_service.get_setting("topic_tags", [
            "💼 работа", "❤️ отношения", "👨‍👩‍👧 семья", "🏥 здоровье",
            "💰 деньги", "🎓 учеба", "🤝 друзья", "🏠 быт"
        ])
    
    keyboard = OnboardingUX.create_selection_keyboard(
        topics, 
        "topic",
        selected_indices=selected_topics,
        max_cols=2,
        done_text="🎉 Завершить анкету"
    )
    
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass  # Ignore if message is the same


async def topics_done_handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_count = len(data.get("selected_topics", set()))
    
    if selected_count == 0:
        await callback.answer("Выберите хотя бы одну тему 😊")
        return
        
    await show_confirmation(callback.message, state)


async def show_confirmation(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    # Get selected emotion/topic counts
    emotions_count = len(data.get('selected_emotions', set()))
    topics_count = len(data.get('selected_topics', set()))
    
    # Build beautiful confirmation text
    text = "🎉 <b>Отлично! Анкета заполнена</b>\n\n"
    text += "📝 <b>Ваши данные:</b>\n\n"
    
    # Personal info
    if data.get('name'):
        text += f"• 👤 Имя: <b>{data.get('name')}</b>\n"
    if data.get('age'):
        text += f"• 🎂 Возраст: <b>{data.get('age')} лет</b>\n"
    if data.get('city'):
        text += f"• 🏙️ Город: <b>{data.get('city')}</b>\n"
    
    text += f"\n• 💭 Эмоций выбрано: <b>{emotions_count}</b>"
    text += f"\n• 💬 Тем выбрано: <b>{topics_count}</b>\n\n"
    
    text += "Всё верно? Вы можете с лёгкостью создать новую анкету в любое время через меню."
    
    keyboard = OnboardingUX.create_button_keyboard([
        ("✅ Всё отлично!", "survey_confirm"),
        ("✏️ Изменить", "survey_edit")
    ])
    
    await UXHelper.smooth_edit_text(
        message,
        text,
        reply_markup=keyboard,
        typing_delay=1.5
    )


async def survey_confirm_handler(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id)
    user_name = callback.from_user.first_name or "друг"
    data = await state.get_data()
    
    # Show completion animation
    completion_steps = [
        "✨ Сохраняю ваши данные...",
        "🧠 Настраиваю персонализацию...",
        "🎯 Готовлю для вас лучший опыт..."
    ]
    
    final_text = f"🎉 <b>Добро пожаловать, {data.get('name', user_name)}!</b>\n\nТеперь я знаю вас лучше и смогу:\n• 💬 Понимать ваши эмоции\n• 🎯 Подбирать подходящие советы\n• 🌟 Создать комфортную атмосферу\n\n💭 <b>Расскажите, что у вас на душе?</b>"
    
    await UXHelper.progress_edit(
        callback.message,
        completion_steps,
        final_text,
        step_delay=1.0
    )
    
    async with async_session() as session:
        user_service = UserService(session)
        
        # Get user and update profile
        user = await user_service.get_or_create_user(telegram_id)
        
        user.name = data.get('name')
        user.age = data.get('age')
        user.gender = data.get('gender')
        user.city = data.get('city')
        user.timezone = data.get('timezone')
        user.emotion_tags = list(data.get('selected_emotions', []))
        user.topic_tags = list(data.get('selected_topics', []))
        
        await session.commit()
        
        # Log survey completion
        await user_service.log_event(user.id, "onboarding_done")
    
    # Show main menu after completing survey
    from .profile import show_main_menu
    main_menu = await show_main_menu()
    
    await UXHelper.smooth_answer(
        callback.message,
        "🏠 <b>Главное меню:</b>",
        reply_markup=main_menu,
        typing_delay=1.5
    )
    await state.clear()


def register_survey_handlers(dp: Dispatcher):
    dp.callback_query.register(survey_name_handler, F.data == "survey_name")
    dp.message.register(name_input_handler, SurveyStates.waiting_name)
    
    dp.callback_query.register(survey_age_handler, F.data == "survey_age")
    dp.message.register(age_input_handler, SurveyStates.waiting_age)
    
    dp.callback_query.register(survey_gender_handler, F.data == "survey_gender")
    dp.callback_query.register(gender_handler, F.data.startswith("gender_"))
    
    dp.callback_query.register(survey_city_handler, F.data == "survey_city")
    dp.message.register(city_input_handler, SurveyStates.waiting_city)
    
    dp.callback_query.register(emotion_handler, F.data.startswith("emotion_") & ~F.data.endswith("_done"))
    dp.callback_query.register(emotions_done_handler, F.data == "emotion_done")
    
    dp.callback_query.register(topic_handler, F.data.startswith("topic_") & ~F.data.endswith("_done"))
    dp.callback_query.register(topics_done_handler, F.data == "topic_done")
    
    dp.callback_query.register(survey_confirm_handler, F.data == "survey_confirm")
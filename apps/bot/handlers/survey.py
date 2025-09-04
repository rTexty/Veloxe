from aiogram import Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
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
    waiting_timezone = State()
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
        typing_delay=0.3
    )
    await state.set_state(SurveyStates.waiting_name)


async def name_input_handler(message: types.Message, state: FSMContext):
    import re
    
    name = message.text.strip()
    
    # Валидация имени - защита от команд и некорректного ввода
    if not name or len(name) < 1 or len(name) > 30:
        await UXHelper.smooth_answer(
            message,
            "👤 Пожалуйста, укажите ваше имя (1-30 символов)",
            typing_delay=0.3
        )
        return
    
    # Проверка на команды бота
    if name.startswith('/') or name.startswith('@'):
        await UXHelper.smooth_answer(
            message,
            "📝 <b>Давайте сначала завершим анкету!</b>\n\nВы сейчас заполняете профиль. Пожалуйста, ответьте на текущий вопрос или нажмите /start для начала сначала.",
            typing_delay=0.3
        )
        return
    
    # Проверка на подозрительные символы
    if re.search(r'[<>{}[\]()=+*&%$#!^~`|\\]', name):
        await UXHelper.smooth_answer(
            message,
            "👤 Используйте только буквы, цифры, пробелы и базовые знаки",
            typing_delay=0.3
        )
        return
    
    await state.update_data(name=name)
    
    keyboard = OnboardingUX.create_button_keyboard([
        ("🎂 Указать возраст", "survey_age"),
        ("⏭️ Пропустить", "survey_gender")
    ])
    
    # Безопасное отображение имени
    safe_name = name.replace('<', '&lt;').replace('>', '&gt;')
    response_text = f"🌟 <b>Приятно познакомиться, {safe_name}!</b>\n\nПродолжаем знакомство?"
    
    await UXHelper.smooth_answer(
        message, 
        response_text, 
        reply_markup=keyboard,
        typing_delay=0.3
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
        typing_delay=0.2
    )
    await state.set_state(SurveyStates.waiting_age)


async def age_input_handler(message: types.Message, state: FSMContext):
    user_input = message.text.strip()
    
    # Проверка на команды бота
    if user_input.startswith('/'):
        await UXHelper.smooth_answer(
            message,
            "📝 Сейчас нужно указать ваш возраст цифрами.\nКоманды можно использовать после завершения анкеты.",
            typing_delay=0.3
        )
        return
    
    try:
        age = int(user_input)
        if 10 <= age <= 120:
            await state.update_data(age=age)
            await show_gender_selection(message, state)
        else:
            await UXHelper.smooth_answer(
                message,
                "🤔 Похоже, возраст необычный...\nПопробуйте ещё раз (10-120 лет)",
                typing_delay=0.3
            )
    except ValueError:
        await UXHelper.smooth_answer(
            message,
            "😅 Пожалуйста, напишите возраст просто цифрами",
            typing_delay=0.3
        )


async def survey_gender_handler(callback: types.CallbackQuery, state: FSMContext):
    await show_gender_selection(callback.message, state)


async def show_gender_selection(message: types.Message, state: FSMContext = None):
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
        typing_delay=0.3
    )
    
    # Устанавливаем правильное состояние
    if state:
        await state.set_state(SurveyStates.waiting_gender)


async def gender_text_handler(message: types.Message, state: FSMContext):
    """Обработка текстового ввода во время выбора пола"""
    user_input = message.text.strip()
    
    if user_input.startswith('/'):
        await UXHelper.smooth_answer(
            message,
            "📝 Сейчас нужно выбрать пол кнопками выше.\nКоманды можно использовать после завершения анкеты.",
            typing_delay=0.3
        )
    else:
        await UXHelper.smooth_answer(
            message,
            "🤷 Пожалуйста, выберите пол кнопками выше или нажмите «Пропустить»",
            typing_delay=0.3
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
        typing_delay=0.2
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
        typing_delay=0.2
    )
    await state.set_state(SurveyStates.waiting_city)


async def city_input_handler(message: types.Message, state: FSMContext):
    from utils.timezone_helper import TimezoneHelper
    import re
    
    city = message.text.strip()
    
    # Валидация города - защита от команд и некорректного ввода
    if not city or len(city) < 2 or len(city) > 50:
        await UXHelper.smooth_answer(
            message,
            "🏙️ Пожалуйста, укажите название города (2-50 символов)",
            typing_delay=0.3
        )
        return
    
    # Проверка на команды бота
    if city.startswith('/') or city.startswith('@'):
        await UXHelper.smooth_answer(
            message,
            "🏙️ Пожалуйста, укажите реальный город, а не команду 😊",
            typing_delay=0.3
        )
        return
    
    # Проверка на подозрительные символы
    if re.search(r'[<>{}[\]()=+*&%$#@!^~`|\\]', city):
        await UXHelper.smooth_answer(
            message,
            "🏙️ Используйте только буквы, цифры, пробелы и дефисы",
            typing_delay=0.3
        )
        return
    # Определяем часовой пояс с помощью улучшенной логики
    timezone = TimezoneHelper.get_timezone_from_city(city)
    
    await state.update_data(city=city)
    
    if not timezone:
        # Показываем выбор часового пояса
        await show_timezone_selection(message, state)
    else:
        # Автоматически определился часовой пояс, переходим дальше
        await state.update_data(timezone=timezone)
        
        # Transition message с безопасным отображением города
        safe_city = city.replace('<', '&lt;').replace('>', '&gt;')
        transition_text = f"🏙️ <b>{safe_city}</b> — красивый город!\n\n⏭️ Переходим к следующему шагу..."
        transition_msg = await UXHelper.smooth_answer(
            message, 
            transition_text,
            typing_delay=0.3
        )
        
        await show_emotions_selection(transition_msg, state)


async def show_timezone_selection(message: types.Message, state: FSMContext):
    """Показать выбор часового пояса"""
    question_text = OnboardingUX.format_survey_question(
        "Выберите ваш часовой пояс",
        4, 6,
        "Это поможет мне учитывать ваше время 🕐"
    )
    
    timezones = [
        "🇰🇿 МСК-1 (UTC+2)", "🇷🇺 МСК (UTC+3)", "🇷🇺 МСК+1 (UTC+4)",
        "🇰🇿 МСК+2 (UTC+5)", "🇰🇿 МСК+3 (UTC+6)", "🇷🇺 МСК+4 (UTC+7)",
        "🇷🇺 МСК+5 (UTC+8)", "🇷🇺 МСК+6 (UTC+9)", "🇷🇺 МСК+7 (UTC+10)",
        "🇷🇺 МСК+8 (UTC+11)", "🇷🇺 МСК+9 (UTC+12)"
    ]
    
    keyboard = OnboardingUX.create_selection_keyboard(
        timezones, 
        "timezone",
        max_cols=1,  # По одному в строке для удобства
        done_text="✅ Выбрать",
        single_choice=True  # Только один выбор
    )
    
    await UXHelper.smooth_edit_text(
        message,
        question_text,
        reply_markup=keyboard,
        typing_delay=0.3
    )
    
    # Устанавливаем состояние ожидания выбора часового пояса
    await state.set_state(SurveyStates.waiting_timezone)


async def timezone_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора часового пояса"""
    timezone_index = callback.data.replace("timezone_", "")
    
    # Маппинг индексов на реальные часовые пояса
    timezone_map = {
        "0": "Europe/Kaliningrad",  # UTC+2
        "1": "Europe/Moscow",       # UTC+3
        "2": "Europe/Samara",       # UTC+4
        "3": "Asia/Yekaterinburg",  # UTC+5
        "4": "Asia/Omsk",           # UTC+6
        "5": "Asia/Krasnoyarsk",    # UTC+7
        "6": "Asia/Irkutsk",        # UTC+8
        "7": "Asia/Yakutsk",        # UTC+9
        "8": "Asia/Vladivostok",    # UTC+10
        "9": "Asia/Magadan",        # UTC+11
        "10": "Asia/Kamchatka"      # UTC+12
    }
    
    selected_timezone = timezone_map.get(timezone_index, "Europe/Moscow")
    await state.update_data(timezone=selected_timezone)
    
    # Получаем данные для отображения города
    data = await state.get_data()
    city = data.get('city', 'ваш город')
    safe_city = city.replace('<', '&lt;').replace('>', '&gt;')
    
    # Переходим к эмоциям
    transition_text = f"🏙️ <b>{safe_city}</b> — красивый город!\n\n⏭️ Переходим к следующему шагу..."
    await UXHelper.smooth_edit_text(
        callback.message,
        transition_text,
        typing_delay=0.3
    )
    
    await callback.answer("✅ Часовой пояс выбран!")
    await show_emotions_selection(callback.message, state)


async def timezone_text_handler(message: types.Message, state: FSMContext):
    """Обработка текстового ввода во время выбора часового пояса"""
    user_input = message.text.strip()
    
    if user_input.startswith('/'):
        await UXHelper.smooth_answer(
            message,
            "🕐 Сейчас нужно выбрать часовой пояс кнопками выше.\nКоманды можно использовать после завершения анкеты.",
            typing_delay=0.3
        )
    else:
        await UXHelper.smooth_answer(
            message,
            "🕐 Пожалуйста, выберите часовой пояс кнопками выше",
            typing_delay=0.3
        )


async def show_emotions_selection(message: types.Message, state: FSMContext = None):
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
        typing_delay=0.4
    )
    
    # Устанавливаем правильное состояние
    if state:
        await state.set_state(SurveyStates.waiting_emotions)


async def emotions_text_handler(message: types.Message, state: FSMContext):
    """Обработка текстового ввода во время выбора эмоций"""
    user_input = message.text.strip()
    
    if user_input.startswith('/'):
        await UXHelper.smooth_answer(
            message,
            "💭 Сейчас нужно выбрать эмоции кнопками выше.\nКоманды можно использовать после завершения анкеты.",
            typing_delay=0.3
        )
    else:
        await UXHelper.smooth_answer(
            message,
            "💭 Пожалуйста, выберите эмоции кнопками выше или нажмите «Продолжить»",
            typing_delay=0.3
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
        typing_delay=0.3
    )
    
    await show_topics_selection(callback.message, state)


async def show_topics_selection(message: types.Message, state: FSMContext = None):
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
        typing_delay=0.3
    )
    
    # Устанавливаем правильное состояние
    if state:
        await state.set_state(SurveyStates.waiting_topics)


async def topics_text_handler(message: types.Message, state: FSMContext):
    """Обработка текстового ввода во время выбора тем"""
    user_input = message.text.strip()
    
    if user_input.startswith('/'):
        await UXHelper.smooth_answer(
            message,
            "💬 Сейчас нужно выбрать темы кнопками выше.\nКоманды можно использовать после завершения анкеты.",
            typing_delay=0.3
        )
    else:
        await UXHelper.smooth_answer(
            message,
            "💬 Пожалуйста, выберите темы кнопками выше или нажмите «Завершить анкету»",
            typing_delay=0.3
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
        typing_delay=0.4
    )


async def survey_confirm_handler(callback: types.CallbackQuery, state: FSMContext):
    telegram_id = str(callback.from_user.id)
    user_name = callback.from_user.first_name or "друг"
    data = await state.get_data()
    
    # ВРЕМЕННО ОТКЛЮЧЕНА АНИМАЦИЯ ЗАГРУЗКИ
    # completion_steps = [
    #     "✨ Сохраняю ваши данные...",
    #     "🧠 Настраиваю персонализацию...",
    #     "🎯 Готовлю для вас лучший опыт..."
    # ]
    
    final_text = f"🎉 <b>Добро пожаловать, {data.get('name', user_name)}!</b>\n\nТеперь я знаю вас лучше и смогу:\n• 💬 Понимать ваши эмоции\n• 🎯 Подбирать подходящие советы\n• 🌟 Создать комфортную атмосферу\n\n💭 <b>Расскажите, что у вас на душе?</b>"
    
    # await UXHelper.progress_edit(
    #     callback.message,
    #     completion_steps,
    #     final_text,
    #     step_delay=1.0
    # )
    
    # Показываем сразу финальный текст без анимации
    await UXHelper.smooth_edit_text(
        callback.message,
        final_text,
        typing_delay=0.3
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
        typing_delay=0.4
    )
    await state.clear()


def register_survey_handlers(dp: Dispatcher):
    dp.callback_query.register(survey_name_handler, F.data == "start_onboarding")
    dp.callback_query.register(survey_name_handler, F.data == "survey_name")
    dp.message.register(name_input_handler, SurveyStates.waiting_name)
    
    dp.callback_query.register(survey_age_handler, F.data == "survey_age")
    dp.message.register(age_input_handler, SurveyStates.waiting_age)
    
    dp.callback_query.register(survey_gender_handler, F.data == "survey_gender")
    dp.callback_query.register(gender_handler, F.data.startswith("gender_"))
    dp.message.register(gender_text_handler, SurveyStates.waiting_gender)
    
    dp.callback_query.register(survey_city_handler, F.data == "survey_city")
    dp.message.register(city_input_handler, SurveyStates.waiting_city)
    
    dp.callback_query.register(timezone_handler, F.data.startswith("timezone_"))
    dp.message.register(timezone_text_handler, SurveyStates.waiting_timezone)
    
    dp.callback_query.register(emotion_handler, F.data.startswith("emotion_") & ~F.data.endswith("_done"))
    dp.callback_query.register(emotions_done_handler, F.data == "emotion_done")
    dp.message.register(emotions_text_handler, SurveyStates.waiting_emotions)
    
    dp.callback_query.register(topic_handler, F.data.startswith("topic_") & ~F.data.endswith("_done"))
    dp.callback_query.register(topics_done_handler, F.data == "topic_done")
    dp.message.register(topics_text_handler, SurveyStates.waiting_topics)
    
    dp.callback_query.register(survey_confirm_handler, F.data == "survey_confirm")
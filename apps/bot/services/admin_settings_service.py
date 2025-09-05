from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import sys
sys.path.append('../../../')

from .settings_service import SettingsService


class AdminSettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings_service = SettingsService(session)
    
    async def initialize_default_settings(self):
        """Initialize default bot settings"""
        
        # Frequent settings (easily changed by admins)
        await self._set_if_not_exists("daily_message_limit", 5, "frequent", "Daily free message limit per user")
        await self._set_if_not_exists("policy_version", "v1", "frequent", "Current privacy policy version")
        
        # Consent texts
        await self._set_if_not_exists(
            "consent_welcome_text", 
            "Привет! Здесь будет комфортно и безопасно. ❗️Это не замена психотерапии. В кризисных ситуациях звоните 112. 📄 Подробнее об условиях... Готовы продолжить?",
            "frequent", 
            "Welcome text shown during consent gate"
        )
        
        await self._set_if_not_exists(
            "full_privacy_policy",
            "Полная политика конфиденциальности:\n\n1. Мы не врачи и не психотерапевты\n2. Не сохраняем содержание ваших сообщений\n3. В кризисных ситуациях обращайтесь к специалистам\n4. Вы можете удалить свои данные в любое время",
            "frequent",
            "Full privacy policy text"
        )
        
        # Survey texts
        await self._set_if_not_exists(
            "survey_intro_text",
            "Расскажите немного о себе, чтобы я мог лучше вас понимать.",
            "frequent",
            "Survey introduction text"
        )
        
        # Emotion and topic tags
        await self._set_if_not_exists(
            "emotion_tags",
            [
                "😰 тревога", "😥 чувство вины", "😡 злость", "😞 усталость",
                "😔 грусть", "😨 страх", "😤 раздражение", "😟 беспокойство",
                "😢 печаль", "😮‍💨 стресс", "😓 беспомощность", "😵‍💫 растерянность"
            ],
            "frequent",
            "Available emotion tags for user selection"
        )
        
        await self._set_if_not_exists(
            "topic_tags",
            [
                "💼 работа", "❤️ отношения", "👨‍👩‍👧 семья", "🏥 здоровье",
                "💰 деньги", "🎓 учеба", "🤝 друзья", "🏠 быт",
                "🎯 цели", "⚖️ решения", "🌱 саморазвитие", "😴 сон"
            ],
            "frequent", 
            "Available topic tags for user selection"
        )
        
        # Payment settings
        await self._set_if_not_exists("cryptocloud_api_key", "", "expert", "CryptoCloud API key")
        await self._set_if_not_exists("cryptocloud_shop_id", "", "expert", "CryptoCloud shop ID")
        await self._set_if_not_exists("support_contact", "@support", "frequent", "Support contact username")
        
        # Payment text templates
        await self._set_if_not_exists(
            "payment_success_text",
            "✅ Оплата прошла успешно!\n\nВаша подписка активирована. Теперь у вас безлимитное общение с ботом. Приятного использования! 🎉",
            "frequent",
            "Payment success message template"
        )
        
        await self._set_if_not_exists(
            "payment_failed_text",
            "❌ Оплата не прошла. Попробуйте другой способ или обратитесь в поддержку {support_contact}",
            "frequent", 
            "Payment failure message template"
        )
        
        await self._set_if_not_exists(
            "subscription_reminder_24h_template",
            "🔔 {name}, ваша подписка истекает через 24 часа!\n\nХотите продлить для продолжения безлимитного общения?",
            "frequent",
            "24-hour subscription reminder template"
        )
        
        await self._set_if_not_exists(
            "subscription_reminder_expiry_template", 
            "⚠️ {name}, ваша подписка истекает сегодня!\n\nПродлите сейчас, чтобы сохранить безлимитное общение.",
            "frequent",
            "Expiration day reminder template"
        )
        
        await self._set_if_not_exists("subscription_reminders_enabled", True, "frequent", "Enable subscription expiration reminders")
        
        # Payment retry templates
        await self._set_if_not_exists(
            "payment_retry_template",
            "❌ Оплата не прошла (попытка {attempt} из {max_attempts})\n\nПопробуйте:\n• Другой способ оплаты\n• Проверить данные карты\n• Повторить через несколько минут",
            "frequent",
            "Payment retry message template"
        )
        
        await self._set_if_not_exists(
            "payment_max_attempts_template",
            "😔 К сожалению, платеж не прошел после нескольких попыток.\n\nДля помощи с оплатой обратитесь в поддержку: {support_contact}\n\nМы поможем решить любые проблемы!",
            "frequent",
            "Message when max payment attempts reached"
        )
        
        # Expert settings (advanced configuration)
        await self._set_if_not_exists("memory_window_size", 15, "expert", "Number of recent messages to include in GPT context")
        await self._set_if_not_exists("max_blocks_per_reply", 3, "expert", "Maximum blocks to split GPT response into")
        await self._set_if_not_exists("min_block_length", 30, "expert", "Minimum length of text block before merging")
        await self._set_if_not_exists("delay_between_blocks_min", 2200, "expert", "Minimum delay between blocks in milliseconds")
        await self._set_if_not_exists("delay_between_blocks_max", 4200, "expert", "Maximum delay between blocks in milliseconds")
        await self._set_if_not_exists("typing_duration_base", 1.5, "expert", "Base typing duration in seconds")
        await self._set_if_not_exists("typing_duration_per_word", 0.1, "expert", "Additional typing duration per word in seconds")
        
        # Long-term memory settings
        await self._set_if_not_exists("long_memory_enabled", True, "expert", "Enable long-term memory anchors system")
        await self._set_if_not_exists("memory_anchor_ttl_days", 90, "expert", "Days to keep memory anchors in Redis cache")
        await self._set_if_not_exists("max_anchors_per_user", 20, "expert", "Maximum memory anchors per user")
        
        # Crisis settings
        await self._set_if_not_exists(
            "crisis_keywords",
            [
                "умереть", "умру", "суицид", "покончить", "повеситься", 
                "убить себя", "не хочу жить", "нет смысла жить", "конец",
                "прыгнуть", "таблетки", "смерть", "убийство себя"
            ],
            "expert",
            "Keywords that trigger crisis mode"
        )
        
        await self._set_if_not_exists("crisis_ping_freeze_hours", 12, "expert", "Hours to freeze pings after crisis event")
        
        await self._set_if_not_exists(
            "crisis_response_text",
            "Мне очень жаль, что тебе так тяжело. Я не могу заменить живого специалиста, но хочу, чтобы ты сейчас получил помощь.\n\n🆘 Горячая линия: 8 800 2000 122\n📞 Экстренные службы: 112",
            "frequent",
            "Text shown when crisis is detected"
        )
        
        await self._set_if_not_exists(
            "crisis_safety_phrase",
            "я не причиню себе вред",
            "expert", 
            "Phrase user must type to exit crisis mode"
        )
        
        await self._set_if_not_exists(
            "crisis_help_contacts",
            "🆘 ЭКСТРЕННАЯ ПОМОЩЬ\n\n📞 Всероссийская горячая линия:\n8 800 2000 122 (круглосуточно, бесплатно)\n\n🚑 Экстренные службы: 112\n\n💬 Онлайн поддержка:\n• Телефон доверия: 8-495-988-44-34\n• Чат поддержки: pomogi.org",
            "frequent",
            "Crisis help contacts shown to users"
        )
        
        # Progressive ping timing settings
        await self._set_if_not_exists("progressive_ping_1_delay", 30, "frequent", "Minutes before sending first progressive ping")
        await self._set_if_not_exists("progressive_ping_2_delay", 120, "frequent", "Minutes after first ping to send second ping")
        await self._set_if_not_exists("progressive_ping_3_delay", 1440, "frequent", "Minutes after second ping to send third ping")
        
        # Session settings
        await self._set_if_not_exists("session_close_timeout", 48, "expert", "Hours before closing inactive session")
        await self._set_if_not_exists("allowed_ping_hours_start", 10, "frequent", "Start of allowed ping hours")
        await self._set_if_not_exists("allowed_ping_hours_end", 21, "frequent", "End of allowed ping hours")
        
        # Legacy idle_ping_delay (mapped to progressive_ping_1_delay for backward compatibility)
        await self._set_if_not_exists("idle_ping_delay", 30, "expert", "Minutes before sending idle ping (legacy)")
        
        # Ping system settings
        await self._set_if_not_exists("ping_enabled", True, "frequent", "Enable automatic ping system")
        await self._set_if_not_exists("ping_ai_generation_enabled", False, "frequent", "Enable AI generation of ping texts")
        
        # AI ping generation system prompt
        await self._set_if_not_exists(
            "ping_ai_system_prompt",
            "Ты эмпатичный психологический чат-бот. Создай короткое (до 50 символов), теплое сообщение для проверки связи с пользователем. Используй эмодзи. Варьируй тон от мягкого до заботливого в зависимости от уровня пинга. Не используй вопросы прямо о проблемах, будь деликатным.",
            "expert",
            "System prompt for AI-generated ping messages"
        )
        
        # Progressive ping templates
        await self._set_if_not_exists(
            "progressive_ping_1_templates",
            [
                "Ты ещё здесь? Я на связи 💙",
                "Как дела, {name}? Я слушаю 🤗", 
                "Всё в порядке? 💭",
                "Если нужно поговорить, я здесь ✨"
            ],
            "frequent",
            "Templates for first progressive ping (level 1)"
        )
        
        await self._set_if_not_exists(
            "progressive_ping_2_templates",
            [
                "👋 {name}, думаю о тебе. Как настроение?",
                "🌟 Хочется узнать, как ты себя чувствуешь?", 
                "💭 {name}, поделишься, что у тебя на душе?",
                "🤗 Как прошло время? Расскажешь?"
            ],
            "frequent",
            "Templates for second progressive ping (level 2)"
        )
        
        await self._set_if_not_exists(
            "progressive_ping_3_templates",
            [
                "🌈 {name}, я беспокоюсь. Как ты?",
                "💙 Давно не слышал от тебя. Всё ли хорошо?", 
                "☀️ {name}, надеюсь, у тебя все в порядке. Я здесь, если нужно поговорить",
                "🫂 Скучаю по нашим разговорам. Как дела?"
            ],
            "frequent",
            "Templates for third progressive ping (level 3)"
        )
        
        # Idle ping templates  
        await self._set_if_not_exists(
            "idle_ping_templates",
            [
                "Ты ещё здесь? Я на связи 💙",
                "Как дела? Я слушаю 🤗", 
                "Всё в порядке? 💭",
                "Если нужно поговорить, я здесь ✨"
            ],
            "frequent",
            "Templates for idle ping messages (within session)"
        )
        
        # Error handling settings
        await self._set_if_not_exists("api_timeout", 30, "expert", "API timeout in seconds")
        await self._set_if_not_exists("max_retry_attempts", 2, "expert", "Maximum retry attempts for failed API calls")
        await self._set_if_not_exists("payment_retry_attempts", 3, "expert", "Maximum payment retry attempts")
        
        # System texts
        await self._set_if_not_exists(
            "error_messages",
            {
                "api_timeout": "Кажется, я задумался... Попробуем ещё раз?",
                "payment_failed": "Оплата не прошла. Попробуйте другой способ или обратитесь в поддержку",
                "service_maintenance": "Сервис обновляется, скоро вернусь"
            },
            "frequent",
            "Error messages shown to users"
        )
        
        # Paywall settings
        await self._set_if_not_exists(
            "paywall_text",
            "💳 <b>Подписка</b>\n\nДля продолжения общения необходима подписка. Выберите подходящий тариф:",
            "frequent",
            "Text shown when paywall is triggered"
        )
        
        # Subscription settings
        await self._set_if_not_exists(
            "subscription_plans",
            [
                {"name": "7 дней", "days": 7, "price": 199, "currency": "RUB", "discount": 0},
                {"name": "30 дней", "days": 30, "price": 599, "currency": "RUB", "discount": 10},
                {"name": "90 дней", "days": 90, "price": 1499, "currency": "RUB", "discount": 17}
            ],
            "frequent",
            "Available subscription plans"
        )
        
        # Onboarding settings
        await self._set_if_not_exists("emotion_max", 10, "frequent", "Maximum emotions user can select")
        await self._set_if_not_exists("topic_max", 8, "frequent", "Maximum topics user can select")
        
        # GPT System Prompt (ВАЖНО!)
        await self._set_if_not_exists(
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
- Будь кратким но теплым

ФОРМАТ ОТВЕТОВ:
- Максимум 3 абзаца
- Каждый абзац - отдельная мысль
- Используй переносы строк между абзацами
- Не более 200 слов общего объема""",
            "frequent",
            "System prompt for GPT - defines bot personality and behavior"
        )
        
        # GPT Model settings
        await self._set_if_not_exists("gpt_model", "gpt-4", "expert", "GPT model to use")
        await self._set_if_not_exists("gpt_temperature", 0.8, "expert", "GPT temperature (creativity)")
        await self._set_if_not_exists("gpt_max_tokens", 800, "expert", "Maximum tokens in GPT response")
        
        # Greeting Generation Settings
        await self._set_if_not_exists(
            "greeting_prompt",
            """Ты генерируешь персонализированные приветствия для бота эмоциональной поддержки.

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
Только текст приветствия, без кавычек и пояснений.""",
            "frequent",
            "System prompt for generating personalized greetings"
        )
        
        await self._set_if_not_exists(
            "greeting_fallback_templates",
            [
                "Привет, {name}! Как дела? 😊",
                "Здравствуй, {name}! Рад тебя видеть 🌸", 
                "Привет! Как настроение, {name}? 💭",
                "Добро пожаловать, {name}! Что у тебя на душе? ✨",
                "Приветик, {name}! Расскажи, как прошел день? 🌈",
                "Привет снова, {name}! Соскучился 💙",
                "Здравствуй! Хорошо, что ты зашел, {name} 🌟"
            ],
            "frequent",
            "Fallback greeting templates when GPT fails"
        )
        
        await self._set_if_not_exists("greeting_enabled", True, "frequent", "Enable GPT-powered dynamic greetings")
        await self._set_if_not_exists("greeting_cache_ttl", 300, "expert", "Seconds to cache generated greetings")
        
        # Welcome message for new users
        await self._set_if_not_exists(
            "welcome_message",
            """👋 Добро пожаловать!

Я — твой личный помощник для эмоциональной поддержки. Здесь ты можешь:

• 💬 Поделиться переживаниями в безопасной обстановке
• 🧘‍♀️ Получить поддержку и понимание  
• 📈 Отследить свое эмоциональное состояние
• 🌟 Найти покой и баланс в жизни

🔒 <b>Полная конфиденциальность:</b> все разговоры остаются между нами.

⚠️ <i>Важно: это дополнение к профессиональной помощи, а не замена. В кризисных ситуациях обращайтесь к специалистам или звоните 112.</i>""",
            "frequent",
            "Welcome message shown to new users on first /start"
        )
        
        # Continue button prompt
        await self._set_if_not_exists(
            "continue_prompt",
            "Продолжи мысль, дай развернутый совет или поддержку. Будь эмпатичным и полезным. Не повторяйся, добавь что-то новое к разговору.",
            "frequent",
            "Prompt used when user clicks 'Continue' button"
        )
        
        # Analytics settings
        await self._set_if_not_exists("analytics_retention_days", 90, "expert", "Days to keep analytics data")
        await self._set_if_not_exists("log_user_messages", False, "expert", "Whether to log user message content (GDPR sensitive)")
        
        print("✅ Default settings initialized")
    
    async def _set_if_not_exists(self, key: str, value, category: str, description: str):
        """Set setting only if it doesn't exist"""
        existing = await self.settings_service.get_setting(key)
        if existing is None:
            await self.settings_service.set_setting(key, value, category, description)
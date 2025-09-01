from aiogram import Dispatcher
from .start import register_start_handlers
from .consent import register_consent_handlers
from .survey import register_survey_handlers
from .dialog import register_dialog_handlers
from .crisis import register_crisis_handlers
from .subscription import register_subscription_handlers
from .profile import register_profile_handlers
from .menu import register_menu_handlers


def register_handlers(dp: Dispatcher):
    register_start_handlers(dp)
    register_consent_handlers(dp)
    register_survey_handlers(dp)
    register_crisis_handlers(dp)
    register_subscription_handlers(dp)
    register_profile_handlers(dp)
    register_menu_handlers(dp)
    register_dialog_handlers(dp)  # Register last (lowest priority)
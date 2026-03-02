"""Keyboards package"""

from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.payment_kb import get_plan_keyboard, get_period_keyboard, get_payment_method_keyboard
from bot.keyboards.subscription_kb import get_subscription_keyboard, get_device_keyboard
from bot.keyboards.admin_kb import get_admin_menu, get_admin_action_keyboard
from bot.keyboards.inline_kb import get_cancel_button, get_back_button, get_confirm_button

__all__ = [
    "get_main_menu",
    "get_plan_keyboard",
    "get_period_keyboard",
    "get_payment_method_keyboard",
    "get_subscription_keyboard",
    "get_device_keyboard",
    "get_admin_menu",
    "get_admin_action_keyboard",
    "get_cancel_button",
    "get_back_button",
    "get_confirm_button",
]

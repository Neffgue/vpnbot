"""FSM states for payment flow"""

from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    """States for payment process"""
    
    # Payment flow
    waiting_plan_selection = State()
    waiting_period_selection = State()
    waiting_payment_confirmation = State()
    waiting_payment_method = State()
    waiting_payment_completion = State()


class SubscriptionStates(StatesGroup):
    """States for subscription management"""
    
    waiting_subscription_action = State()
    waiting_renewal = State()


class DeviceStates(StatesGroup):
    """States for device management flow"""
    
    waiting_device_type = State()
    waiting_device_confirmation = State()
    waiting_device_deletion = State()


class EmailStates(StatesGroup):
    """States for email input flow"""
    
    waiting_email = State()


# AdminStates is defined in bot/states/admin_states.py — do NOT duplicate here

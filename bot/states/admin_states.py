"""FSM states for admin operations"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """States for admin panel operations"""
    
    waiting_admin_action = State()
    waiting_ban_user_id = State()
    waiting_ban_reason = State()
    waiting_unban_user_id = State()
    waiting_add_balance_user_id = State()
    waiting_add_balance_amount = State()
    waiting_add_balance_reason = State()
    waiting_broadcast_message = State()
    waiting_broadcast_confirm = State()

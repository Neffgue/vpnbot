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

    # Тарифы — изменение цены
    waiting_price_plan_id = State()
    waiting_price_amount = State()

    # Кнопки меню — загрузка изображения
    waiting_btn_image_id = State()
    waiting_btn_image_photo = State()

    # Инструкции — загрузка изображения к шагу
    waiting_instr_step_device = State()
    waiting_instr_step_num = State()
    waiting_instr_step_photo = State()

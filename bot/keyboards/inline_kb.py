"""Inline keyboard utilities"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_cancel_button() -> InlineKeyboardMarkup:
    """Get cancel button"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="cancel"
                )
            ]
        ]
    )
    
    return keyboard


def get_back_button(callback: str = "back_to_menu") -> InlineKeyboardMarkup:
    """Get back button"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=callback
                )
            ]
        ]
    )
    
    return keyboard


def get_confirm_button(callback: str = "confirm") -> InlineKeyboardMarkup:
    """Get confirmation button"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=callback
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data="cancel"
                )
            ]
        ]
    )
    
    return keyboard


def get_link_button(text: str, url: str, back_callback: str = "back_to_menu") -> InlineKeyboardMarkup:
    """Get button with link"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text,
                    url=url
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=back_callback
                )
            ]
        ]
    )
    
    return keyboard


def get_yes_no_keyboard(callback_yes: str = "yes", callback_no: str = "no") -> InlineKeyboardMarkup:
    """Get yes/no keyboard"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да",
                    callback_data=callback_yes
                ),
                InlineKeyboardButton(
                    text="❌ Нет",
                    callback_data=callback_no
                )
            ]
        ]
    )
    
    return keyboard

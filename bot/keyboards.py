from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.parser import ALL_CATEGORIES

MENU_TODAY = "📅 Сегодня"
MENU_MONTH = "📊 Месяц"
MENU_HISTORY = "🧾 История"
MENU_EXPORT = "📤 Экспорт"


class ExpenseAction(CallbackData, prefix="exp"):
    action: str  # pick | set | delete | back
    expense_id: int
    category_idx: int = -1


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_TODAY), KeyboardButton(text=MENU_MONTH)],
            [KeyboardButton(text=MENU_HISTORY), KeyboardButton(text=MENU_EXPORT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Например: 350 кофе",
    )


def expense_actions(expense_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="🏷 Категория", callback_data=ExpenseAction(action="pick", expense_id=expense_id)
    )
    builder.button(
        text="🗑 Удалить", callback_data=ExpenseAction(action="delete", expense_id=expense_id)
    )
    return builder.as_markup()


def category_picker(expense_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for idx, category in enumerate(ALL_CATEGORIES):
        builder.button(
            text=category,
            callback_data=ExpenseAction(action="set", expense_id=expense_id, category_idx=idx),
        )
    builder.button(
        text="← Назад", callback_data=ExpenseAction(action="back", expense_id=expense_id)
    )
    builder.adjust(2)
    return builder.as_markup()

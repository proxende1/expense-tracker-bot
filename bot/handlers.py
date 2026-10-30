from datetime import datetime
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import Config
from bot.db import Database, Expense
from bot.keyboards import (
    MENU_EXPORT,
    MENU_HISTORY,
    MENU_MONTH,
    MENU_TODAY,
    ExpenseAction,
    category_picker,
    expense_actions,
    main_menu,
)
from bot.parser import ALL_CATEGORIES, parse_amount, parse_expense
from bot.reports import (
    day_bounds,
    expenses_to_csv,
    format_category_report,
    format_expense_line,
    format_money,
    month_bounds,
    month_title,
)

router = Router()

HELP_TEXT = """<b>Как пользоваться</b>

Просто напишите сумму и комментарий:
• <code>350 кофе</code>
• <code>такси 1 200</code>
• <code>4999,90 кроссовки</code>

Категория определится автоматически — её можно поменять кнопкой под расходом.

<b>Команды</b>
/today — расходы за сегодня
/month — статистика за месяц
/history — последние 10 трат
/budget 50000 — задать бюджет на месяц
/undo — удалить последнюю трату
/export — выгрузить месяц в CSV
"""


def _now(config: Config) -> datetime:
    return datetime.now(config.timezone)


def _expense_card(expense: Expense, config: Config) -> str:
    note = f"\n📝 {escape(expense.note)}" if expense.note else ""
    return (
        f"✅ Записал: <b>{format_money(expense.amount_cents, config.currency)}</b>\n"
        f"{escape(expense.category)}{note}"
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    name = escape(message.from_user.first_name or "друг")
    await message.answer(
        f"Привет, {name}! 👋\nЯ помогу вести учёт расходов.\n\n{HELP_TEXT}",
        reply_markup=main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_menu())


@router.message(Command("today"))
@router.message(F.text == MENU_TODAY)
async def cmd_today(message: Message, db: Database, config: Config) -> None:
    start, end = day_bounds(_now(config))
    expenses = await db.list_between(message.from_user.id, start, end)
    if not expenses:
        await message.answer("Сегодня трат ещё не было 🎉")
        return
    total = sum(e.amount_cents for e in expenses)
    lines = [format_expense_line(e, config.currency, config.timezone) for e in expenses]
    await message.answer(
        "<b>Сегодня</b>\n\n"
        + "\n".join(lines)
        + f"\n\n<b>Итого: {format_money(total, config.currency)}</b>"
    )


@router.message(Command("month"))
@router.message(F.text == MENU_MONTH)
async def cmd_month(message: Message, db: Database, config: Config) -> None:
    now = _now(config)
    start, end = month_bounds(now)
    user_id = message.from_user.id
    totals = await db.totals_by_category(user_id, start, end)
    budget = await db.get_budget(user_id)
    await message.answer(format_category_report(month_title(now), totals, config.currency, budget))


@router.message(Command("history"))
@router.message(F.text == MENU_HISTORY)
async def cmd_history(message: Message, db: Database, config: Config) -> None:
    expenses = await db.list_recent(message.from_user.id, limit=10)
    if not expenses:
        await message.answer("История пуста. Напишите, например, <code>350 кофе</code>.")
        return
    lines = [format_expense_line(e, config.currency, config.timezone) for e in expenses]
    await message.answer("<b>Последние траты</b>\n\n" + "\n".join(lines))


@router.message(Command("budget"))
async def cmd_budget(
    message: Message, command: CommandObject, db: Database, config: Config
) -> None:
    user_id = message.from_user.id
    if not command.args:
        budget = await db.get_budget(user_id)
        current = format_money(budget, config.currency) if budget else "не задан"
        await message.answer(
            f"Бюджет на месяц: <b>{current}</b>\nЧтобы изменить: <code>/budget 50000</code>"
        )
        return
    cents = parse_amount(command.args.strip())
    if cents is None:
        await message.answer("Не понял сумму. Пример: <code>/budget 50000</code>")
        return
    await db.set_budget(user_id, cents)
    await message.answer(f"💰 Бюджет на месяц: <b>{format_money(cents, config.currency)}</b>")


@router.message(Command("undo"))
async def cmd_undo(message: Message, db: Database, config: Config) -> None:
    removed = await db.delete_last(message.from_user.id)
    if removed is None:
        await message.answer("Удалять нечего.")
        return
    await message.answer(
        f"↩️ Удалил: {format_money(removed.amount_cents, config.currency)} — "
        f"{escape(removed.category)}"
    )


@router.message(Command("export"))
@router.message(F.text == MENU_EXPORT)
async def cmd_export(message: Message, db: Database, config: Config) -> None:
    now = _now(config)
    start, end = month_bounds(now)
    expenses = await db.list_between(message.from_user.id, start, end)
    if not expenses:
        await message.answer("За этот месяц выгружать нечего.")
        return
    document = BufferedInputFile(
        expenses_to_csv(expenses, config.timezone),
        filename=f"expenses_{now:%Y_%m}.csv",
    )
    await message.answer_document(document, caption=f"Расходы: {month_title(now)}")


@router.message(F.text)
async def add_expense(message: Message, db: Database, config: Config) -> None:
    parsed = parse_expense(message.text)
    if parsed is None:
        await message.answer(
            "Не нашёл сумму 🤔 Напишите, например, <code>350 кофе</code> или /help"
        )
        return
    expense = await db.add_expense(
        message.from_user.id, parsed.amount_cents, parsed.category, parsed.note
    )
    await message.answer(_expense_card(expense, config), reply_markup=expense_actions(expense.id))


@router.callback_query(ExpenseAction.filter())
async def on_expense_action(
    callback: CallbackQuery, callback_data: ExpenseAction, db: Database, config: Config
) -> None:
    user_id = callback.from_user.id
    expense = await db.get_expense(user_id, callback_data.expense_id)
    if expense is None:
        await callback.answer("Эта запись уже удалена", show_alert=True)
        return

    match callback_data.action:
        case "pick":
            await callback.message.edit_reply_markup(reply_markup=category_picker(expense.id))
        case "back":
            await callback.message.edit_reply_markup(reply_markup=expense_actions(expense.id))
        case "set" if 0 <= callback_data.category_idx < len(ALL_CATEGORIES):
            category = ALL_CATEGORIES[callback_data.category_idx]
            await db.update_category(user_id, expense.id, category)
            updated = await db.get_expense(user_id, expense.id)
            await callback.message.edit_text(
                _expense_card(updated, config), reply_markup=expense_actions(expense.id)
            )
        case "delete":
            await db.delete_expense(user_id, expense.id)
            await callback.message.edit_text(
                f"🗑 <s>{format_money(expense.amount_cents, config.currency)} — "
                f"{escape(expense.category)}</s>"
            )
    await callback.answer()

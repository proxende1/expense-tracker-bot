"""Форматирование отчётов: периоды, суммы, текстовые диаграммы, CSV."""

import csv
import io
from collections.abc import Iterable
from datetime import datetime, timedelta, tzinfo
from html import escape

from bot.db import Expense

BAR_WIDTH = 10

# fmt: off
MONTHS_RU = (
    "январь", "февраль", "март", "апрель", "май", "июнь",
    "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь",
)
# fmt: on


def day_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def month_bounds(now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def month_title(now: datetime) -> str:
    return f"{MONTHS_RU[now.month - 1].capitalize()} {now.year}"


def format_money(cents: int, currency: str) -> str:
    rubles, kopecks = divmod(abs(cents), 100)
    sign = "-" if cents < 0 else ""
    whole = f"{rubles:,}".replace(",", " ")
    if kopecks:
        return f"{sign}{whole},{kopecks:02d} {currency}"
    return f"{sign}{whole} {currency}"


def make_bar(value: int, maximum: int, width: int = BAR_WIDTH) -> str:
    if maximum <= 0:
        return ""
    filled = max(1, round(value / maximum * width)) if value > 0 else 0
    return "█" * filled + "░" * (width - filled)


def format_category_report(
    title: str,
    totals: list[tuple[str, int]],
    currency: str,
    budget_cents: int | None = None,
) -> str:
    if not totals:
        return f"<b>{escape(title)}</b>\n\nРасходов пока нет."

    grand_total = sum(total for _, total in totals)
    biggest = totals[0][1]
    lines = [f"<b>{escape(title)}</b>", ""]
    for category, total in totals:
        share = round(total / grand_total * 100)
        lines.append(f"{escape(category)} — {format_money(total, currency)} ({share}%)")
        lines.append(f"<code>{make_bar(total, biggest)}</code>")
    lines += ["", f"<b>Итого: {format_money(grand_total, currency)}</b>"]

    if budget_cents:
        left = budget_cents - grand_total
        used = round(grand_total / budget_cents * 100)
        if left >= 0:
            lines.append(f"Бюджет: использовано {used}%, осталось {format_money(left, currency)}")
        else:
            lines.append(f"⚠️ Бюджет превышен на {format_money(-left, currency)} ({used}%)")
    return "\n".join(lines)


def format_expense_line(expense: Expense, currency: str, tz: tzinfo) -> str:
    when = expense.created_at.astimezone(tz).strftime("%d.%m %H:%M")
    note = f" · {escape(expense.note)}" if expense.note else ""
    amount = format_money(expense.amount_cents, currency)
    return f"<code>{when}</code> {amount} — {escape(expense.category)}{note}"


def expenses_to_csv(expenses: Iterable[Expense], tz: tzinfo) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Дата", "Сумма", "Категория", "Комментарий"])
    for expense in expenses:
        writer.writerow(
            [
                expense.created_at.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
                f"{expense.amount_cents / 100:.2f}".replace(".", ","),
                expense.category,
                expense.note,
            ]
        )
    # utf-8-sig, чтобы Excel сразу открыл кириллицу без кракозябр
    return buffer.getvalue().encode("utf-8-sig")

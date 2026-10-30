from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from bot.db import Expense
from bot.reports import (
    day_bounds,
    expenses_to_csv,
    format_category_report,
    format_money,
    make_bar,
    month_bounds,
    month_title,
)

MSK = ZoneInfo("Europe/Moscow")
NBSP = " "


def test_format_money():
    assert format_money(35000, "₽") == f"350{NBSP}₽"
    assert format_money(123456789, "₽") == f"1{NBSP}234{NBSP}567,89{NBSP}₽"
    assert format_money(5, "$") == f"0,05{NBSP}$"
    assert format_money(-1000, "₽") == f"-10{NBSP}₽"


def test_day_bounds_respects_timezone():
    now = datetime(2026, 10, 30, 1, 30, tzinfo=MSK)
    start, end = day_bounds(now)
    assert start == datetime(2026, 10, 30, tzinfo=MSK)
    assert (end - start).days == 1


def test_month_bounds_december_rollover():
    start, end = month_bounds(datetime(2026, 12, 31, 23, 59, tzinfo=MSK))
    assert start == datetime(2026, 12, 1, tzinfo=MSK)
    assert end == datetime(2027, 1, 1, tzinfo=MSK)


def test_month_title():
    assert month_title(datetime(2026, 10, 1)) == "Октябрь 2026"


def test_make_bar():
    assert make_bar(10, 10) == "█" * 10
    assert make_bar(1, 1000) == "█" + "░" * 9  # маленькая трата всё равно видна
    assert make_bar(0, 10) == "░" * 10
    assert make_bar(5, 0) == ""


def test_report_empty():
    assert "Расходов пока нет" in format_category_report("Октябрь", [], "₽")


def test_report_with_budget():
    totals = [("🍔 Еда", 3000_00), ("🏠 Дом", 1000_00)]
    text = format_category_report("Октябрь", totals, "₽", 10000_00)
    assert "75%" in text and "25%" in text
    assert f"Итого: 4{NBSP}000{NBSP}₽" in text
    assert f"осталось 6{NBSP}000{NBSP}₽" in text


def test_report_budget_exceeded():
    text = format_category_report("Октябрь", [("🍔 Еда", 1500_00)], "₽", 1000_00)
    assert "превышен" in text


def test_report_escapes_html():
    text = format_category_report("<b>", [("<script>", 100)], "₽")
    assert "<script>" not in text


def test_csv_export():
    created = datetime(2026, 10, 30, 9, 0, tzinfo=UTC)
    expense = Expense(1, 1, 35050, "🍔 Еда", "кофе; с собой", created)
    data = expenses_to_csv([expense], MSK)
    assert data.startswith("﻿".encode())
    text = data.decode("utf-8-sig")
    assert "Дата;Сумма;Категория;Комментарий" in text
    assert '2026-10-30 12:00;350,50;🍔 Еда;"кофе; с собой"' in text

import pytest

from bot.parser import DEFAULT_CATEGORY, detect_category, parse_amount, parse_expense


@pytest.mark.parametrize(
    ("text", "cents", "note"),
    [
        ("350 кофе", 35000, "кофе"),
        ("кофе 350", 35000, "кофе"),
        ("1 200 такси до дома", 120000, "такси до дома"),
        ("такси 1 200", 120000, "такси"),
        ("4999,90 кроссовки", 499990, "кроссовки"),
        ("99.5 жвачка", 9950, "жвачка"),
        ("500р обед", 50000, "обед"),
        ("500 руб. обед", 50000, "обед"),
        ("обед 500₽", 50000, "обед"),
        ("150", 15000, ""),
        ("  42  ", 4200, ""),
    ],
)
def test_parse_expense_amount_and_note(text, cents, note):
    parsed = parse_expense(text)
    assert parsed is not None
    assert parsed.amount_cents == cents
    assert parsed.note == note


@pytest.mark.parametrize(
    "text",
    ["", "привет", "/start", "0 кофе", "кофе", "-100 кофе", "1000000000 яхта"],
)
def test_parse_expense_rejects_invalid(text):
    assert parse_expense(text) is None


def test_word_starting_with_r_is_note_not_currency():
    parsed = parse_expense("350 рыба")
    assert parsed is not None
    assert parsed.note == "рыба"


@pytest.mark.parametrize(
    ("note", "category"),
    [
        ("кофе с собой", "🍔 Еда"),
        ("Продукты в Пятёрочке", "🍔 Еда"),
        ("такси до дома", "🚕 Транспорт"),
        ("коммуналка за октябрь", "🏠 Дом"),
        ("подписка на музыку", "🎮 Развлечения"),
        ("аптека", "💊 Здоровье"),
        ("подарок маме", "👕 Покупки"),
        ("мобильная связь", "📱 Связь"),
        ("что-то непонятное", DEFAULT_CATEGORY),
        ("", DEFAULT_CATEGORY),
    ],
)
def test_detect_category(note, category):
    assert detect_category(note) == category


@pytest.mark.parametrize(
    ("raw", "cents"),
    [
        ("50000", 5000000),
        ("50 000", 5000000),
        ("12,5", 1250),
        ("abc", None),
        ("NaN", None),
        ("1e5", None),
        ("0", None),
    ],
)
def test_parse_amount(raw, cents):
    assert parse_amount(raw) == cents

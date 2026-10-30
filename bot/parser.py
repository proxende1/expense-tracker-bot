"""Разбор сообщений вида «350 кофе» / «такси 1 200,50» в расход."""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# Ключевые слова — это основы слов: сравниваем через startswith,
# поэтому «продукт» поймает и «продукты», и «продуктовый».
# fmt: off
CATEGORIES: dict[str, tuple[str, ...]] = {
    "🍔 Еда": (
        "еда", "еду", "кофе", "обед", "ужин", "завтрак", "продукт", "ресторан",
        "кафе", "пицц", "шаурм", "перекус", "доставк", "фастфуд", "суши",
    ),
    "🚕 Транспорт": (
        "такси", "метро", "автобус", "бензин", "топливо", "проезд",
        "электричк", "парковк", "каршеринг", "самокат", "поезд",
    ),
    "🏠 Дом": ("аренд", "квартплат", "жкх", "коммунал", "интернет", "ремонт", "мебел"),
    "🎮 Развлечения": ("кино", "игр", "концерт", "подписк", "steam", "театр", "музей"),
    "💊 Здоровье": ("аптек", "врач", "лекарств", "спортзал", "фитнес", "стоматолог", "анализ"),
    "👕 Покупки": ("одежд", "обувь", "техник", "подар", "книг", "косметик"),
    "📱 Связь": ("телефон", "мобильн", "связь", "симк"),
}
# fmt: on
DEFAULT_CATEGORY = "📦 Другое"
ALL_CATEGORIES: tuple[str, ...] = (*CATEGORIES, DEFAULT_CATEGORY)

MAX_AMOUNT = Decimal("1000000000")

# 1200 | 1 200 | 1 200,50 | 99.9
_NUM = r"(?:\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,]\d{1,2})?"
_CUR = r"(?:\s*(?:₽|р\.?|руб\.?|rub))?"
_LEADING = re.compile(rf"^\s*(?P<amount>{_NUM}){_CUR}(?:\s+(?P<note>.+?))?\s*$", re.IGNORECASE)
_TRAILING = re.compile(rf"^\s*(?P<note>.+?)\s+(?P<amount>{_NUM}){_CUR}\s*$", re.IGNORECASE)
_AMOUNT_ONLY = re.compile(rf"^\s*{_NUM}\s*$")
_WORD = re.compile(r"[\wё]+", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedExpense:
    amount_cents: int
    category: str
    note: str


def detect_category(note: str) -> str:
    words = _WORD.findall(note.lower())
    for category, stems in CATEGORIES.items():
        if any(word.startswith(stem) for word in words for stem in stems):
            return category
    return DEFAULT_CATEGORY


def parse_amount(raw: str) -> int | None:
    if not _AMOUNT_ONLY.match(raw):
        return None
    normalized = raw.replace(" ", "").replace(" ", "").replace(",", ".")
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        return None
    if value <= 0 or value >= MAX_AMOUNT:
        return None
    return int((value * 100).to_integral_value())


def parse_expense(text: str) -> ParsedExpense | None:
    """Возвращает расход или None, если в тексте нет суммы."""
    if not text or text.startswith("/"):
        return None
    match = _LEADING.match(text) or _TRAILING.match(text)
    if not match:
        return None
    cents = parse_amount(match["amount"])
    if cents is None:
        return None
    note = (match["note"] or "").strip()
    return ParsedExpense(amount_cents=cents, category=detect_category(note), note=note)

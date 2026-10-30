# 💸 Expense Tracker Bot

[![CI](https://github.com/proxende1/expense-tracker-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/proxende1/expense-tracker-bot/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0)
![License](https://img.shields.io/badge/license-MIT-green)

Telegram-бот для учёта личных расходов. Пишете `350 кофе`, он сам определяет категорию, считает статистику за месяц, следит за бюджетом и выгружает данные в CSV.

## Возможности

- **Быстрый ввод.** Сумму можно писать до или после комментария: `350 кофе`, `такси 1 200`, `4999,90 кроссовки`, `500р обед`
- **Автокатегории.** Еда, транспорт, дом, развлечения, здоровье, покупки, связь. Категорию можно поменять кнопкой под записью
- **Статистика за месяц** с текстовыми диаграммами и долей каждой категории
- **Бюджет:** показывает, сколько осталось или на сколько превышен лимит
- **История и отмена:** последние траты, `/undo`, удаление кнопкой
- **Экспорт в CSV,** который корректно открывается в Excel (UTF-8 BOM, разделитель `;`)
- **Учёт часового пояса,** чтобы «сегодня» и «месяц» считались по вашему времени

## Как это выглядит

```
Октябрь 2026

🍔 Еда — 12 400 ₽ (52%)
██████████
🚕 Транспорт — 6 800 ₽ (28%)
█████░░░░░
🏠 Дом — 4 700 ₽ (20%)
████░░░░░░

Итого: 23 900 ₽
Бюджет: использовано 80%, осталось 6 100 ₽
```

## Команды

| Команда | Что делает |
|---|---|
| `/start`, `/help` | Приветствие и справка |
| `/today` | Траты за сегодня |
| `/month` | Статистика по категориям за месяц |
| `/history` | Последние 10 трат |
| `/budget 50000` | Задать бюджет на месяц (без аргумента показывает текущий) |
| `/undo` | Удалить последнюю трату |
| `/export` | CSV-файл за текущий месяц |

## Запуск

1. Получите токен у [@BotFather](https://t.me/BotFather).
2. Склонируйте репозиторий и создайте `.env`:

```bash
git clone https://github.com/proxende1/expense-tracker-bot.git
cd expense-tracker-bot
cp .env.example .env   # впишите BOT_TOKEN
```

### Через Docker

```bash
docker compose up -d --build
```

### Локально

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m bot
```

## Настройки (`.env`)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | Токен бота (обязательно) |
| `DB_PATH` | `data/expenses.db` | Файл базы SQLite |
| `CURRENCY` | `₽` | Символ валюты |
| `TIMEZONE` | `Europe/Moscow` | Часовой пояс |

## Структура

```
bot/
├── __main__.py   # точка входа: бот, диспетчер, команды меню
├── config.py     # загрузка настроек из .env
├── parser.py     # разбор «350 кофе» → сумма, категория, комментарий
├── db.py         # SQLite через aiosqlite (суммы в копейках, время в UTC)
├── reports.py    # периоды, форматирование денег, диаграммы, CSV
├── keyboards.py  # reply-меню и inline-кнопки (CallbackData)
└── handlers.py   # хендлеры команд, сообщений и колбэков
tests/            # pytest: парсер, БД, отчёты, сквозные тесты хендлеров
```

## Разработка

```bash
pip install -r requirements-dev.txt
pytest          # 60+ тестов, включая сквозные через Dispatcher с фейковой сессией API
ruff check .
ruff format .
```

Сквозные тесты (`tests/test_handlers.py`) прогоняют апдейты через настоящий диспетчер aiogram. Вместо Telegram API подставлена сессия, которая записывает исходящие запросы, поэтому токен и сеть для тестов не нужны.

## Стек

Python 3.11+ · aiogram 3 · aiosqlite · pytest · ruff · Docker · GitHub Actions

## Лицензия

[MIT](LICENSE)

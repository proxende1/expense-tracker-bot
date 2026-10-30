"""Сквозные тесты: апдейт → диспетчер aiogram → хендлер → БД → запрос к API."""

from aiogram.methods import EditMessageText, SendDocument, SendMessage

from bot.keyboards import ExpenseAction
from tests.conftest import USER_ID, callback_update, message_update


async def feed(dispatcher, bot, db, config, update):
    await dispatcher.feed_update(bot, update, db=db, config=config)


def sent_texts(session):
    return [r.text for r in session.requests if isinstance(r, (SendMessage, EditMessageText))]


async def test_start_shows_help(dispatcher, bot, session, db, config):
    await feed(dispatcher, bot, db, config, message_update("/start"))
    assert "Привет, Тест" in sent_texts(session)[0]


async def test_add_expense_flow(dispatcher, bot, session, db, config):
    await feed(dispatcher, bot, db, config, message_update("350 кофе"))

    [expense] = await db.list_recent(USER_ID)
    assert expense.amount_cents == 35000
    assert expense.category == "🍔 Еда"
    request = session.requests[-1]
    assert "Записал" in request.text
    assert request.reply_markup is not None


async def test_unknown_text_gets_hint(dispatcher, bot, session, db, config):
    await feed(dispatcher, bot, db, config, message_update("привет"))
    assert "Не нашёл сумму" in sent_texts(session)[0]
    assert await db.list_recent(USER_ID) == []


async def test_change_category_via_callback(dispatcher, bot, session, db, config):
    expense = await db.add_expense(USER_ID, 1000, "📦 Другое", "штука")
    data = ExpenseAction(action="set", expense_id=expense.id, category_idx=1).pack()
    await feed(dispatcher, bot, db, config, callback_update(data))

    updated = await db.get_expense(USER_ID, expense.id)
    assert updated.category == "🚕 Транспорт"
    assert any(isinstance(r, EditMessageText) for r in session.requests)


async def test_delete_via_callback(dispatcher, bot, session, db, config):
    expense = await db.add_expense(USER_ID, 1000, "📦 Другое")
    data = ExpenseAction(action="delete", expense_id=expense.id).pack()
    await feed(dispatcher, bot, db, config, callback_update(data))
    assert await db.get_expense(USER_ID, expense.id) is None


async def test_month_report_with_budget(dispatcher, bot, session, db, config):
    await feed(dispatcher, bot, db, config, message_update("/budget 10 000"))
    await feed(dispatcher, bot, db, config, message_update("2500 продукты", update_id=2))
    await feed(dispatcher, bot, db, config, message_update("/month", update_id=3))

    report = sent_texts(session)[-1]
    assert "🍔 Еда" in report
    assert "осталось" in report


async def test_undo(dispatcher, bot, session, db, config):
    await feed(dispatcher, bot, db, config, message_update("100 кофе"))
    await feed(dispatcher, bot, db, config, message_update("/undo", update_id=2))
    assert await db.list_recent(USER_ID) == []
    assert "Удалил" in sent_texts(session)[-1]


async def test_export_sends_csv(dispatcher, bot, session, db, config):
    await feed(dispatcher, bot, db, config, message_update("100 кофе"))
    await feed(dispatcher, bot, db, config, message_update("/export", update_id=2))
    document = session.requests[-1]
    assert isinstance(document, SendDocument)
    assert document.document.filename.endswith(".csv")

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio

from bot.db import Database

USER = 1
OTHER_USER = 2


@pytest_asyncio.fixture
async def db():
    database = Database(":memory:")
    await database.connect()
    yield database
    await database.close()


async def test_add_and_get(db):
    expense = await db.add_expense(USER, 35000, "🍔 Еда", "кофе")
    loaded = await db.get_expense(USER, expense.id)
    assert loaded == expense


async def test_users_are_isolated(db):
    expense = await db.add_expense(USER, 100, "🍔 Еда")
    assert await db.get_expense(OTHER_USER, expense.id) is None
    assert await db.delete_expense(OTHER_USER, expense.id) is False
    assert await db.update_category(OTHER_USER, expense.id, "x") is False
    assert await db.list_recent(OTHER_USER) == []


async def test_update_category(db):
    expense = await db.add_expense(USER, 100, "📦 Другое")
    assert await db.update_category(USER, expense.id, "🚕 Транспорт")
    assert (await db.get_expense(USER, expense.id)).category == "🚕 Транспорт"


async def test_delete_last_removes_newest(db):
    base = datetime(2026, 10, 1, tzinfo=UTC)
    await db.add_expense(USER, 100, "a", created_at=base)
    newest = await db.add_expense(USER, 200, "b", created_at=base + timedelta(hours=1))
    removed = await db.delete_last(USER)
    assert removed.id == newest.id
    assert [e.amount_cents for e in await db.list_recent(USER)] == [100]
    await db.delete_last(USER)
    assert await db.delete_last(USER) is None


async def test_list_between_and_totals(db):
    base = datetime(2026, 10, 15, 12, tzinfo=UTC)
    await db.add_expense(USER, 100, "🍔 Еда", created_at=base)
    await db.add_expense(USER, 300, "🍔 Еда", created_at=base + timedelta(hours=1))
    await db.add_expense(USER, 1000, "🏠 Дом", created_at=base + timedelta(hours=2))
    await db.add_expense(USER, 9999, "🏠 Дом", created_at=base + timedelta(days=30))

    start, end = base - timedelta(days=1), base + timedelta(days=1)
    assert len(await db.list_between(USER, start, end)) == 3
    assert await db.totals_by_category(USER, start, end) == [("🏠 Дом", 1000), ("🍔 Еда", 400)]


async def test_budget_upsert(db):
    assert await db.get_budget(USER) is None
    await db.set_budget(USER, 5000000)
    await db.set_budget(USER, 7000000)
    assert await db.get_budget(USER) == 7000000


@pytest.mark.parametrize("limit", [1, 5])
async def test_list_recent_limit(db, limit):
    for i in range(7):
        await db.add_expense(USER, i + 1, "x")
    assert len(await db.list_recent(USER, limit=limit)) == limit

"""Хранилище расходов на SQLite. Суммы храним в копейках, время — в UTC."""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS expenses (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    amount_cents INTEGER NOT NULL,
    category     TEXT    NOT NULL,
    note         TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses (user_id, created_at);

CREATE TABLE IF NOT EXISTS budgets (
    user_id      INTEGER PRIMARY KEY,
    amount_cents INTEGER NOT NULL
);
"""


@dataclass(frozen=True)
class Expense:
    id: int
    user_id: int
    amount_cents: int
    category: str
    note: str
    created_at: datetime


def _ts(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def _row_to_expense(row: aiosqlite.Row) -> Expense:
    return Expense(
        id=row["id"],
        user_id=row["user_id"],
        amount_cents=row["amount_cents"],
        category=row["category"],
        note=row["note"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self._path != ":memory:":
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def add_expense(
        self,
        user_id: int,
        amount_cents: int,
        category: str,
        note: str = "",
        created_at: datetime | None = None,
    ) -> Expense:
        created_at = created_at or datetime.now(UTC)
        cursor = await self.conn.execute(
            "INSERT INTO expenses (user_id, amount_cents, category, note, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, amount_cents, category, note, _ts(created_at)),
        )
        await self.conn.commit()
        return Expense(
            id=cursor.lastrowid,
            user_id=user_id,
            amount_cents=amount_cents,
            category=category,
            note=note,
            created_at=datetime.fromisoformat(_ts(created_at)),
        )

    async def get_expense(self, user_id: int, expense_id: int) -> Expense | None:
        async with self.conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
        return _row_to_expense(row) if row else None

    async def update_category(self, user_id: int, expense_id: int, category: str) -> bool:
        cursor = await self.conn.execute(
            "UPDATE expenses SET category = ? WHERE id = ? AND user_id = ?",
            (category, expense_id, user_id),
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def delete_expense(self, user_id: int, expense_id: int) -> bool:
        cursor = await self.conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id)
        )
        await self.conn.commit()
        return cursor.rowcount > 0

    async def delete_last(self, user_id: int) -> Expense | None:
        recent = await self.list_recent(user_id, limit=1)
        if not recent:
            return None
        await self.delete_expense(user_id, recent[0].id)
        return recent[0]

    async def list_recent(self, user_id: int, limit: int = 10) -> list[Expense]:
        async with self.conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        ) as cursor:
            return [_row_to_expense(row) for row in await cursor.fetchall()]

    async def list_between(self, user_id: int, start: datetime, end: datetime) -> list[Expense]:
        async with self.conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? AND created_at >= ? AND created_at < ?"
            " ORDER BY created_at, id",
            (user_id, _ts(start), _ts(end)),
        ) as cursor:
            return [_row_to_expense(row) for row in await cursor.fetchall()]

    async def totals_by_category(
        self, user_id: int, start: datetime, end: datetime
    ) -> list[tuple[str, int]]:
        async with self.conn.execute(
            "SELECT category, SUM(amount_cents) AS total FROM expenses"
            " WHERE user_id = ? AND created_at >= ? AND created_at < ?"
            " GROUP BY category ORDER BY total DESC",
            (user_id, _ts(start), _ts(end)),
        ) as cursor:
            return [(row["category"], row["total"]) for row in await cursor.fetchall()]

    async def set_budget(self, user_id: int, amount_cents: int) -> None:
        await self.conn.execute(
            "INSERT INTO budgets (user_id, amount_cents) VALUES (?, ?)"
            " ON CONFLICT(user_id) DO UPDATE SET amount_cents = excluded.amount_cents",
            (user_id, amount_cents),
        )
        await self.conn.commit()

    async def get_budget(self, user_id: int) -> int | None:
        async with self.conn.execute(
            "SELECT amount_cents FROM budgets WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return row["amount_cents"] if row else None

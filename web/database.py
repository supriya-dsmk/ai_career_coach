"""
SQLite database layer for the Career Coach web application.

Manages users, development plans, and weekly progress tracking.
Uses sqlite3 from the standard library -- no ORM required.
The DB file is stored at ``web/career_coach.db`` (next to this module).

Tables are created automatically when the module is first imported.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Database path  -- sits right beside this file
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).parent / "career_coach.db"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _hash_password(password: str) -> str:
    """Return the SHA-256 hex digest of *password*."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a ``sqlite3.Row`` to a plain ``dict``."""
    return dict(row)


# ---------------------------------------------------------------------------
# Connection / initialisation
# ---------------------------------------------------------------------------
def get_connection() -> sqlite3.Connection:
    """Return a ``sqlite3.Connection`` with ``row_factory = sqlite3.Row``."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they do not already exist."""
    conn = get_connection()
    try:
        conn.executescript(
            """\
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                name          TEXT,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS plans (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER REFERENCES users(id),
                status         TEXT    DEFAULT 'draft',
                plan_markdown  TEXT    NOT NULL,
                agent1_output  TEXT,
                agent2_output  TEXT,
                agent3_output  TEXT,
                input_summary  TEXT,
                timeline_days  INTEGER DEFAULT 90,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accepted_at    TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS progress (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id      INTEGER REFERENCES plans(id),
                week_number  INTEGER NOT NULL,
                task_text    TEXT    NOT NULL,
                completed    BOOLEAN DEFAULT 0,
                completed_at TIMESTAMP,
                notes        TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()

    # Migrations -- add columns that may not exist in older databases
    _migrate_db()


def _migrate_db() -> None:
    """Add columns introduced after the initial schema."""
    conn = get_connection()
    try:
        # Check if timeline_days column exists in plans table
        cursor = conn.execute("PRAGMA table_info(plans)")
        columns = {row["name"] for row in cursor.fetchall()}
        if "timeline_days" not in columns:
            conn.execute(
                "ALTER TABLE plans ADD COLUMN timeline_days INTEGER DEFAULT 90"
            )
            conn.commit()
    finally:
        conn.close()


# ===================================================================
# Users
# ===================================================================
def create_user(email: str, password: str, name: str = "") -> int:
    """Create a new user.  Hash *password* with SHA-256.

    Returns the new user's ``id``.
    Raises ``ValueError`` if a user with the given *email* already exists.
    """
    password_hash = _hash_password(password)
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (?, ?, ?)",
            (email, password_hash, name),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"A user with email '{email}' already exists.")
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> Optional[dict]:
    """Check *email* + *password*.

    Returns ``{"id": ..., "email": ..., "name": ...}`` on success, or
    ``None`` if the credentials are invalid.
    """
    password_hash = _hash_password(password)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, name FROM users WHERE email = ? AND password_hash = ?",
            (email, password_hash),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Return a user dict (``id``, ``email``, ``name``, ``created_at``) or ``None``."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id, email, name, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


# ===================================================================
# Plans
# ===================================================================
def save_plan(
    user_id: int,
    plan_markdown: str,
    agent1_output: str = "",
    agent2_output: str = "",
    agent3_output: str = "",
    input_summary: str = "",
    timeline_days: int = 90,
) -> int:
    """Save a new plan with ``status='draft'``.  Returns the plan ``id``."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO plans
                (user_id, plan_markdown, agent1_output, agent2_output,
                 agent3_output, input_summary, timeline_days)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, plan_markdown, agent1_output, agent2_output,
             agent3_output, input_summary, timeline_days),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def accept_plan(plan_id: int) -> None:
    """Set the plan's status to ``'accepted'`` and record ``accepted_at``."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE plans SET status = 'accepted', accepted_at = ? WHERE id = ?",
            (datetime.now().isoformat(), plan_id),
        )
        conn.commit()
    finally:
        conn.close()


def reject_plan(plan_id: int) -> None:
    """Set the plan's status to ``'rejected'``."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE plans SET status = 'rejected' WHERE id = ?",
            (plan_id,),
        )
        conn.commit()
    finally:
        conn.close()


def update_plan_status(plan_id: int, status: str) -> None:
    """Set the plan's status to an arbitrary value.

    Valid statuses: ``'draft'``, ``'accepted'``, ``'in_progress'``,
    ``'completed'``, ``'rejected'``.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE plans SET status = ? WHERE id = ?",
            (status, plan_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_plan_markdown(plan_id: int, plan_markdown: str) -> None:
    """Update the plan's markdown content (e.g. after user edits)."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE plans SET plan_markdown = ? WHERE id = ?",
            (plan_markdown, plan_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_user_plans(user_id: int) -> list:
    """Return all plans for a user, newest first."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM plans WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_plan(plan_id: int) -> Optional[dict]:
    """Return a single plan dict or ``None``."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_active_plan(user_id: int) -> Optional[dict]:
    """Return the most recent active plan for the user, or ``None``.

    An active plan is one whose status is ``'accepted'``, ``'in_progress'``,
    or ``'completed'``.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT * FROM plans
            WHERE user_id = ? AND status IN ('accepted', 'in_progress', 'completed')
            ORDER BY accepted_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


# ===================================================================
# Progress
# ===================================================================
def init_progress_from_plan(plan_id: int, tasks: list) -> None:
    """Populate the ``progress`` table from a list of task dicts.

    Each element of *tasks* should look like::

        {"week": 1, "task": "Do X"}

    Any existing progress rows for the given *plan_id* are deleted first.
    """
    conn = get_connection()
    try:
        conn.execute("DELETE FROM progress WHERE plan_id = ?", (plan_id,))
        conn.executemany(
            """
            INSERT INTO progress (plan_id, week_number, task_text)
            VALUES (?, ?, ?)
            """,
            [(plan_id, t["week"], t["task"]) for t in tasks],
        )
        conn.commit()
    finally:
        conn.close()


def get_progress(plan_id: int) -> list:
    """Return all progress items for a plan, ordered by ``week_number`` then ``id``."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM progress
            WHERE plan_id = ?
            ORDER BY week_number, id
            """,
            (plan_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def update_task_completion(task_id: int, completed: bool, notes: str = "") -> None:
    """Toggle a task's ``completed`` status.

    Sets ``completed_at`` to the current timestamp when *completed* is
    ``True``; clears it otherwise.
    """
    completed_at = datetime.now().isoformat() if completed else None
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE progress
            SET completed = ?, completed_at = ?, notes = ?
            WHERE id = ?
            """,
            (int(completed), completed_at, notes, task_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_progress_summary(plan_id: int) -> dict:
    """Return an overview of task completion for a plan.

    Returns a dict of the form::

        {
            "total": N,
            "completed": M,
            "by_week": {
                1: {"total": X, "completed": Y},
                ...
            },
        }
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT week_number, completed
            FROM progress
            WHERE plan_id = ?
            ORDER BY week_number
            """,
            (plan_id,),
        ).fetchall()

        total = 0
        completed = 0
        by_week: dict[int, dict[str, int]] = {}

        for row in rows:
            wk = row["week_number"]
            is_done = bool(row["completed"])

            if wk not in by_week:
                by_week[wk] = {"total": 0, "completed": 0}

            by_week[wk]["total"] += 1
            total += 1

            if is_done:
                by_week[wk]["completed"] += 1
                completed += 1

        return {"total": total, "completed": completed, "by_week": by_week}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Auto-initialise on import
# ---------------------------------------------------------------------------
init_db()

from __future__ import annotations

import hashlib
import hmac
import os
import random
import secrets
import sqlite3
import string
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DB_PATH = Path(__file__).parent / "caretrack.db"


def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def password_digest(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
        test_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
        return hmac.compare_digest(test_digest, expected_digest)
    except Exception:
        return False


def generate_temp_password(length: int = 8) -> str:
    # Easy to read but secure
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$"
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_unique_user_id(prefix: str = "W") -> str:
    with connection() as conn:
        for _ in range(50):
            rand_digits = "".join(random.choices(string.digits, k=4))
            uid = f"{prefix}-{rand_digits}"
            exists = conn.execute("SELECT 1 FROM users WHERE username = ?", (uid,)).fetchone()
            if not exists:
                return uid
    return f"{prefix}-{int(datetime.now().timestamp()) % 100000}"


def generate_task_uid() -> str:
    rand_chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"TSK-{rand_chars}"


def init_db(reset: bool = False) -> None:
    with connection() as conn:
        if reset:
            conn.execute("DROP TABLE IF EXISTS submissions")
            conn.execute("DROP TABLE IF EXISTS tasks")
            conn.execute("DROP TABLE IF EXISTS users")
            conn.execute("DROP TABLE IF EXISTS task_settings")
            conn.execute("DROP TABLE IF EXISTS reminder_log")

        # Check if users table needs telegram columns
        user_table_info = conn.execute("PRAGMA table_info(users)").fetchall()
        cols = {row["name"] for row in user_table_info}
        if cols and ("must_change_password" not in cols or "employee_id" not in cols):
            # Legacy table detected, drop and rebuild clean
            conn.execute("DROP TABLE IF EXISTS submissions")
            conn.execute("DROP TABLE IF EXISTS tasks")
            conn.execute("DROP TABLE IF EXISTS users")

        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                employee_id TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                telegram_handle TEXT NOT NULL DEFAULT '',
                email TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'Worker',
                password_hash TEXT NOT NULL,
                must_change_password INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )"""
        )

        user_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "telegram_handle" not in user_cols:
            conn.execute("ALTER TABLE users ADD COLUMN telegram_handle TEXT NOT NULL DEFAULT ''")

        conn.execute(
            """CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_uid TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'Medium',
                due_datetime TEXT NOT NULL,
                proof_requirements TEXT NOT NULL DEFAULT 'Photograph',
                assigned_to_user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Assigned',
                created_by TEXT NOT NULL DEFAULT 'admin',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )

        conn.execute(
            """CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                submitted_by TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                proof_name TEXT NOT NULL DEFAULT '',
                proof_path TEXT NOT NULL DEFAULT '',
                proof_type TEXT NOT NULL DEFAULT 'image',
                status TEXT NOT NULL DEFAULT 'Submitted',
                review_comment TEXT NOT NULL DEFAULT '',
                reviewed_by TEXT DEFAULT '',
                reviewed_at TEXT DEFAULT '',
                submitted_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )"""
        )

        # Seed default Admin if not exists
        admin_exists = conn.execute("SELECT 1 FROM users WHERE LOWER(username) = 'admin'").fetchone()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not admin_exists:
            admin_pwd = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
            conn.execute(
                """INSERT INTO users 
                   (username, full_name, employee_id, phone, telegram_handle, email, role, password_hash, must_change_password, is_active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)""",
                ("admin", "System Administrator", "ADM-001", "1234567890", "@admin_hub", "admin@company.com", "Admin", password_digest(admin_pwd), now)
            )

        # Seed default sample worker if not exists
        worker_exists = conn.execute("SELECT 1 FROM users WHERE LOWER(username) = 'w-1001'").fetchone()
        if not worker_exists:
            worker_pwd = os.getenv("DEFAULT_WORKER_PASSWORD", "worker123")
            conn.execute(
                """INSERT INTO users 
                   (username, full_name, employee_id, phone, telegram_handle, email, role, password_hash, must_change_password, is_active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?)""",
                ("W-1001", "Alex Rivera", "EMP-1001", "+1234567890", "@alex_worker", "alex.worker@company.com", "Worker", password_digest(worker_pwd), now)
            )

            # Sample tasks for initial demo
            sample_tasks = [
                (
                    "TSK-A1001",
                    "Morning Equipment Inspection & Log",
                    "Conduct thorough visual inspection of generators, HVAC units, and fire suppression indicators in Sector 4.",
                    "High",
                    datetime.now().strftime("%Y-%m-%d 18:00:00"),
                    "Photograph of inspection log & gauge readings",
                    "W-1001",
                    "Assigned",
                    "admin",
                    now,
                    now
                ),
                (
                    "TSK-A1002",
                    "Clean Room Sterilization & Audit",
                    "Sterilize workstation surfaces and verify autoclave indicator strips.",
                    "Medium",
                    datetime.now().strftime("%Y-%m-%d 20:00:00"),
                    "Photograph or PDF Audit Checklist",
                    "W-1001",
                    "In Progress",
                    "admin",
                    now,
                    now
                )
            ]
            for st_row in sample_tasks:
                conn.execute(
                    """INSERT OR IGNORE INTO tasks 
                       (task_uid, title, description, priority, due_datetime, proof_requirements, assigned_to_user_id, status, created_by, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    st_row
                )


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),)
        ).fetchone()
        if not row:
            return None
        user_dict = dict(row)
        if not user_dict.get("is_active", 1):
            return None
        if verify_password(password, user_dict["password_hash"]):
            return user_dict
    return None


def change_user_password(username: str, new_password: str) -> bool:
    new_hash = password_digest(new_password)
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE LOWER(username) = LOWER(?)",
            (new_hash, username.strip())
        )
        return cursor.rowcount > 0


def create_worker(
    full_name: str,
    employee_id: str = "",
    phone: str = "",
    telegram_handle: str = "",
    email: str = "",
    username: str | None = None,
    temporary_password: str | None = None,
    must_change_pwd: bool = True
) -> Tuple[bool, str, str]:
    """Creates a worker account. Returns (success, user_id, temp_password)."""
    user_id = username.strip() if username and username.strip() else generate_unique_user_id("W")
    temp_pwd = temporary_password.strip() if temporary_password and temporary_password.strip() else generate_temp_password(8)
    pwd_hash = password_digest(temp_pwd)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with connection() as conn:
            conn.execute(
                """INSERT INTO users 
                   (username, full_name, employee_id, phone, telegram_handle, email, role, password_hash, must_change_password, is_active, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'Worker', ?, ?, 1, ?)""",
                (user_id, full_name.strip(), employee_id.strip(), phone.strip(), telegram_handle.strip(), email.strip(), pwd_hash, 1 if must_change_pwd else 0, now)
            )
        return True, user_id, temp_pwd
    except sqlite3.IntegrityError:
        return False, user_id, "User ID already exists"
    except Exception as e:
        return False, user_id, str(e)


def reset_worker_password(username: str) -> str | None:
    temporary_password = generate_temp_password(8)
    password_hash = password_digest(temporary_password)
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = 1 "
            "WHERE LOWER(username) = LOWER(?) AND role = 'Worker' AND is_active = 1",
            (password_hash, username.strip()),
        )
        return temporary_password if cursor.rowcount else None


def toggle_worker_status(username: str, is_active: bool) -> bool:
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE users SET is_active = ? WHERE LOWER(username) = LOWER(?) AND role = 'Worker'",
            (1 if is_active else 0, username.strip())
        )
        return cursor.rowcount > 0


def list_workers(include_disabled: bool = True) -> List[Dict[str, Any]]:
    with connection() as conn:
        if include_disabled:
            rows = conn.execute("SELECT * FROM users WHERE role = 'Worker' ORDER BY full_name ASC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM users WHERE role = 'Worker' AND is_active = 1 ORDER BY full_name ASC").fetchall()
        return [dict(r) for r in rows]


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),)).fetchone()
        return dict(row) if row else None


# Tasks Management

def create_task(
    title: str,
    description: str,
    priority: str,
    due_datetime: str,
    proof_requirements: str,
    assigned_to_user_id: str,
    created_by: str = "admin"
) -> Tuple[bool, str]:
    task_uid = generate_task_uid()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with connection() as conn:
            conn.execute(
                """INSERT INTO tasks 
                   (task_uid, title, description, priority, due_datetime, proof_requirements, assigned_to_user_id, status, created_by, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'Assigned', ?, ?, ?)""",
                (task_uid, title.strip(), description.strip(), priority, due_datetime, proof_requirements.strip(), assigned_to_user_id, created_by, now, now)
            )
        return True, task_uid
    except Exception as e:
        return False, str(e)


def update_task_status(task_id: int, status: str) -> bool:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connection() as conn:
        cursor = conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, task_id)
        )
        return cursor.rowcount > 0


def reassign_task(task_id: int, new_worker_username: str) -> bool:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connection() as conn:
        worker = conn.execute(
            "SELECT 1 FROM users WHERE LOWER(username) = LOWER(?) AND role = 'Worker' AND is_active = 1",
            (new_worker_username.strip(),),
        ).fetchone()
        task = conn.execute(
            "SELECT assigned_to_user_id, status FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if not worker or not task:
            return False
        if task["status"] not in {"Assigned", "Accepted", "In Progress", "Submitted", "Rejected"}:
            return False
        if task["assigned_to_user_id"].lower() == new_worker_username.strip().lower():
            return False
        cursor = conn.execute(
            "UPDATE tasks SET assigned_to_user_id = ?, status = 'Assigned', updated_at = ? WHERE id = ?",
            (new_worker_username.strip(), now, task_id),
        )
        return cursor.rowcount > 0


def delete_task(task_id: int) -> Tuple[bool, List[str]]:
    with connection() as conn:
        task = conn.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            return False, []
        proof_paths = [
            row["proof_path"]
            for row in conn.execute(
                "SELECT proof_path FROM submissions WHERE task_id = ? AND proof_path != ''",
                (task_id,),
            ).fetchall()
        ]
        conn.execute("DELETE FROM submissions WHERE task_id = ?", (task_id,))
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cursor.rowcount > 0, proof_paths


def list_tasks(
    assigned_to: str | None = None,
    status_filter: str | None = None,
    priority_filter: str | None = None,
    search_query: str | None = None
) -> List[Dict[str, Any]]:
    query = """
        SELECT t.*, u.full_name AS assignee_name, u.phone AS assignee_phone, u.telegram_handle AS assignee_telegram, u.email AS assignee_email
        FROM tasks t
        LEFT JOIN users u ON LOWER(t.assigned_to_user_id) = LOWER(u.username)
        WHERE 1=1
    """
    params: List[Any] = []
    if assigned_to:
        query += " AND LOWER(t.assigned_to_user_id) = LOWER(?)"
        params.append(assigned_to.strip())
    if status_filter and status_filter != "All":
        query += " AND t.status = ?"
        params.append(status_filter)
    if priority_filter and priority_filter != "All":
        query += " AND t.priority = ?"
        params.append(priority_filter)
    if search_query:
        query += " AND (t.title LIKE ? OR t.description LIKE ? OR t.task_uid LIKE ?)"
        s = f"%{search_query.strip()}%"
        params.extend([s, s, s])

    query += " ORDER BY t.due_datetime ASC, t.id DESC"
    with connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_task_by_id(task_id: int) -> Optional[Dict[str, Any]]:
    with connection() as conn:
        row = conn.execute(
            """SELECT t.*, u.full_name AS assignee_name, u.phone AS assignee_phone, u.telegram_handle AS assignee_telegram, u.email AS assignee_email
               FROM tasks t
               LEFT JOIN users u ON LOWER(t.assigned_to_user_id) = LOWER(u.username)
               WHERE t.id = ?""",
            (task_id,)
        ).fetchone()
        return dict(row) if row else None


# Submissions & Proof Management

def create_task_submission(
    task_id: int,
    submitted_by: str,
    notes: str,
    proof_name: str,
    proof_path: str,
    proof_type: str = "image"
) -> Tuple[bool, int]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with connection() as conn:
            cursor = conn.execute(
                """INSERT INTO submissions 
                   (task_id, submitted_by, notes, proof_name, proof_path, proof_type, status, submitted_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'Submitted', ?)""",
                (task_id, submitted_by, notes.strip(), proof_name, proof_path, proof_type, now)
            )
            submission_id = int(cursor.lastrowid)
            # Also update task status to Submitted
            conn.execute(
                "UPDATE tasks SET status = 'Submitted', updated_at = ? WHERE id = ?",
                (now, task_id)
            )
        return True, submission_id
    except Exception:
        return False, 0


def get_submissions_for_task(task_id: int) -> List[Dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            "SELECT * FROM submissions WHERE task_id = ? ORDER BY id DESC",
            (task_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_submission_for_task(task_id: int) -> Optional[Dict[str, Any]]:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM submissions WHERE task_id = ? ORDER BY id DESC LIMIT 1",
            (task_id,)
        ).fetchone()
        return dict(row) if row else None


def review_submission(
    submission_id: int,
    task_id: int,
    status: str,  # 'Approved' or 'Rejected'
    review_comment: str,
    reviewed_by: str
) -> bool:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connection() as conn:
        conn.execute(
            """UPDATE submissions 
               SET status = ?, review_comment = ?, reviewed_by = ?, reviewed_at = ?
               WHERE id = ?""",
            (status, review_comment.strip(), reviewed_by, now, submission_id)
        )
        conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, task_id)
        )
        return True


def get_admin_dashboard_metrics() -> Dict[str, int]:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connection() as conn:
        total_tasks = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        pending_review = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Submitted'").fetchone()[0]
        in_progress = conn.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('Assigned', 'Accepted', 'In Progress')").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Approved'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Rejected'").fetchone()[0]
        overdue = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('Approved') AND due_datetime < ?",
            (now_str,)
        ).fetchone()[0]
        active_workers = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'Worker' AND is_active = 1").fetchone()[0]

    return {
        "total_tasks": total_tasks,
        "pending_review": pending_review,
        "in_progress": in_progress,
        "approved": approved,
        "rejected": rejected,
        "overdue": overdue,
        "active_workers": active_workers
    }


def get_worker_dashboard_metrics(username: str) -> Dict[str, int]:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with connection() as conn:
        total_assigned = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE LOWER(assigned_to_user_id) = LOWER(?)",
            (username,)
        ).fetchone()[0]
        action_required = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE LOWER(assigned_to_user_id) = LOWER(?) AND status IN ('Assigned', 'Accepted', 'In Progress', 'Rejected')",
            (username,)
        ).fetchone()[0]
        submitted = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE LOWER(assigned_to_user_id) = LOWER(?) AND status = 'Submitted'",
            (username,)
        ).fetchone()[0]
        approved = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE LOWER(assigned_to_user_id) = LOWER(?) AND status = 'Approved'",
            (username,)
        ).fetchone()[0]
        overdue = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE LOWER(assigned_to_user_id) = LOWER(?) AND status NOT IN ('Approved') AND due_datetime < ?",
            (username, now_str)
        ).fetchone()[0]

    return {
        "total_assigned": total_assigned,
        "action_required": action_required,
        "submitted": submitted,
        "approved": approved,
        "overdue": overdue
    }

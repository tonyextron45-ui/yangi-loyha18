import aiosqlite
from datetime import datetime, timezone
from typing import Any


class Database:
    def __init__(self, db_path: str, initial_admins: list[int]):
        self.db_path = db_path
        self.initial_admins = initial_admins

    async def init_db(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    file_id TEXT NOT NULL,
                    banner_file_id TEXT DEFAULT '',
                    views_count INTEGER NOT NULL DEFAULT 0,
                    search_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER NOT NULL DEFAULT 0,
                    title TEXT NOT NULL,
                    username TEXT DEFAULT '',
                    invite_link TEXT DEFAULT '',
                    channel_type TEXT NOT NULL CHECK(channel_type IN ('mandatory', 'join_request', 'movie_channel', 'instagram', 'youtube')),
                    joined_count INTEGER NOT NULL DEFAULT 0,
                    left_count INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)

            cursor = await db.execute("PRAGMA table_info(channels)")
            cols = [r[1] for r in await cursor.fetchall()]
            if "joined_count" not in cols:
                await db.execute("ALTER TABLE channels ADD COLUMN joined_count INTEGER NOT NULL DEFAULT 0")
            if "left_count" not in cols:
                await db.execute("ALTER TABLE channels ADD COLUMN left_count INTEGER NOT NULL DEFAULT 0")

            await db.execute("""
                CREATE TABLE IF NOT EXISTS join_requests (
                    channel_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    requested_at TEXT NOT NULL,
                    PRIMARY KEY (channel_id, user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS social_confirmations (
                    channel_row_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    confirmed_at TEXT NOT NULL,
                    PRIMARY KEY (channel_row_id, user_id)
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    added_by INTEGER,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS movie_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    movie_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL CHECK(action_type IN ('search', 'view')),
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (movie_id) REFERENCES movies(id) ON DELETE CASCADE
                )
            """)

            now = datetime.now(timezone.utc).isoformat()
            for admin_id in self.initial_admins:
                await db.execute(
                    "INSERT OR IGNORE INTO admins (user_id, added_by, created_at) VALUES (?, ?, ?)",
                    (admin_id, admin_id, now),
                )

            default_settings = {
                "mandatory_sub_enabled": "1",
                "banner_enabled": "1",
                "welcome_text": (
                    "🎬 <b>Kino Bot</b>ga xush kelibsiz!\n\n"
                    "Istalgan kino kodini yuboring (masalan: <code>1025</code>) va "
                    "filmni darhol tomosha qiling."
                ),
            }
            for k, v in default_settings.items():
                await db.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (k, v),
                )

            await db.commit()

    async def upsert_user(self, user_id: int, username: str | None, full_name: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO users (user_id, username, full_name, created_at, last_active)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    full_name = excluded.full_name,
                    last_active = excluded.last_active
                """,
                (user_id, username or "", full_name or "", now, now),
            )
            await db.commit()

    async def get_all_user_ids(self) -> list[int]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
            return [int(r[0]) for r in rows]

    async def is_admin(self, user_id: int) -> bool:
        if user_id in self.initial_admins:
            return True
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row is not None

    async def add_admin(self, user_id: int, added_by: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO admins (user_id, added_by, created_at) VALUES (?, ?, ?)",
                (user_id, added_by, now),
            )
            await db.commit()

    async def remove_admin(self, user_id: int) -> bool:
        if user_id in self.initial_admins:
            return False
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_admins(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT user_id, added_by, created_at FROM admins ORDER BY user_id ASC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_setting(self, key: str, default: str = "") -> str:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return str(row[0]) if row else default

    async def set_setting(self, key: str, value: str) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            await db.commit()

    async def add_channel(
        self,
        channel_id: int,
        title: str,
        username: str,
        invite_link: str,
        channel_type: str,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO channels (channel_id, title, username, invite_link, channel_type, joined_count, left_count, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 0, 0, 1, ?)
                """,
                (channel_id, title.strip(), username or "", invite_link or "", channel_type, now),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def get_channels(self, channel_type: str | None = None, active_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM channels WHERE 1=1"
        params: list[Any] = []
        if channel_type:
            query += " AND channel_type = ?"
            params.append(channel_type)
        if active_only:
            query += " AND is_active = 1"
        query += " ORDER BY id ASC"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def delete_channel(self, row_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM channels WHERE id = ?", (row_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def increment_channel_joined(self, channel_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE channels SET joined_count = joined_count + 1 WHERE channel_id = ?",
                (channel_id,),
            )
            await db.commit()

    async def increment_channel_left(self, channel_id: int) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE channels SET left_count = left_count + 1 WHERE channel_id = ?",
                (channel_id,),
            )
            await db.commit()

    async def record_join_request(self, channel_id: int, user_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO join_requests (channel_id, user_id, requested_at)
                VALUES (?, ?, ?)
                ON CONFLICT(channel_id, user_id) DO UPDATE SET requested_at = excluded.requested_at
                """,
                (channel_id, user_id, now),
            )
            await db.commit()

    async def has_join_request(self, channel_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM join_requests WHERE channel_id = ? AND user_id = ?",
                (channel_id, user_id),
            )
            row = await cursor.fetchone()
            return row is not None

    async def confirm_social_list(self, channel_row_ids: list[int], user_id: int) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            for row_id in channel_row_ids:
                await db.execute(
                    """
                    INSERT INTO social_confirmations (channel_row_id, user_id, confirmed_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(channel_row_id, user_id) DO UPDATE SET confirmed_at = excluded.confirmed_at
                    """,
                    (row_id, user_id, now),
                )
            await db.commit()

    async def has_confirmed_social(self, channel_row_id: int, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT 1 FROM social_confirmations WHERE channel_row_id = ? AND user_id = ?",
                (channel_row_id, user_id),
            )
            row = await cursor.fetchone()
            return row is not None

    async def add_movie(
        self,
        code: str,
        title: str,
        description: str,
        file_id: str,
        banner_file_id: str = "",
    ) -> tuple[bool, int | None]:
        now = datetime.now(timezone.utc).isoformat()
        clean_code = code.strip()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(
                    """
                    INSERT INTO movies (code, title, description, file_id, banner_file_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (clean_code, title.strip(), description.strip(), file_id, banner_file_id or "", now),
                )
                await db.commit()
                return True, int(cursor.lastrowid)
            except aiosqlite.IntegrityError:
                return False, None

    async def get_movie_by_code(self, code: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM movies WHERE code = ?", (code.strip(),))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_movie_by_id(self, movie_id: int) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def list_movies(self, limit: int = 25, offset: int = 0) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM movies ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def count_movies(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM movies")
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def delete_movie_by_code(self, code: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM movies WHERE code = ?", (code.strip(),))
            await db.commit()
            return cursor.rowcount > 0

    async def update_movie_field(self, movie_id: int, field: str, value: str) -> tuple[bool, str]:
        allowed_fields = {"title", "code", "file_id", "banner_file_id", "description"}
        if field not in allowed_fields:
            return False, "Ruxsat etilmagan maydon."

        clean_val = value.strip() if field in {"title", "code", "description"} else value
        if field == "code" and not clean_val:
            return False, "Kino kodi bo'sh bo'lishi mumkin emas."
        if field == "title" and not clean_val:
            return False, "Kino nomi bo'sh bo'lishi mumkin emas."

        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    f"UPDATE movies SET {field} = ? WHERE id = ?",
                    (clean_val, movie_id),
                )
                await db.commit()
                return True, "Muvaffaqiyatli yangilandi."
            except aiosqlite.IntegrityError:
                return False, "Bu kino kodi allaqachon boshqa filmda ishlatilmoqda!"

    async def log_movie_event(self, movie_id: int, user_id: int, action_type: str) -> None:
        if action_type not in {"search", "view"}:
            return
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO movie_views (movie_id, user_id, action_type, created_at) VALUES (?, ?, ?, ?)",
                (movie_id, user_id, action_type, now),
            )
            if action_type == "search":
                await db.execute(
                    "UPDATE movies SET search_count = search_count + 1 WHERE id = ?",
                    (movie_id,),
                )
            elif action_type == "view":
                await db.execute(
                    "UPDATE movies SET views_count = views_count + 1 WHERE id = ?",
                    (movie_id,),
                )
            await db.commit()

    async def get_stats(self) -> dict[str, Any]:
        today_prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            c = await db.execute("SELECT COUNT(*) AS cnt FROM users")
            total_users = int((await c.fetchone())["cnt"])

            c = await db.execute("SELECT COUNT(*) AS cnt FROM users WHERE created_at LIKE ?", (f"{today_prefix}%",))
            today_users = int((await c.fetchone())["cnt"])

            c = await db.execute("SELECT COUNT(*) AS cnt FROM movies")
            total_movies = int((await c.fetchone())["cnt"])

            c = await db.execute("SELECT COUNT(*) AS cnt FROM movie_views WHERE action_type = 'search'")
            total_searches = int((await c.fetchone())["cnt"])

            c = await db.execute("SELECT COUNT(*) AS cnt FROM movie_views WHERE action_type = 'view'")
            total_views = int((await c.fetchone())["cnt"])

            c = await db.execute(
                "SELECT code, title, search_count FROM movies ORDER BY search_count DESC, id DESC LIMIT 5"
            )
            top_searched = [dict(r) for r in await c.fetchall()]

            c = await db.execute(
                "SELECT code, title, views_count FROM movies ORDER BY views_count DESC, id DESC LIMIT 5"
            )
            top_viewed = [dict(r) for r in await c.fetchall()]

            return {
                "total_users": total_users,
                "today_users": today_users,
                "total_movies": total_movies,
                "total_searches": total_searches,
                "total_views": total_views,
                "top_searched": top_searched,
                "top_viewed": top_viewed,
            }

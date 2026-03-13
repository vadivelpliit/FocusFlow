"""
Run migrations on app startup (and optionally via scripts/migrate_auth).
Adds auth tables, user_id, complexity, reasoning to existing DBs.
Idempotent: safe to run on every startup.
"""
import logging
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _table_exists(engine: Engine, name: str) -> bool:
    return name in inspect(engine).get_table_names()


def _column_exists(engine: Engine, table: str, col: str) -> bool:
    return col in [c["name"] for c in inspect(engine).get_columns(table)]


def _run(engine: Engine, *statements: str) -> None:
    for s in statements:
        if not s.strip():
            continue
        with engine.connect() as conn:
            conn.execute(text(s))
            conn.commit()


def run_migrations(engine: Engine) -> None:
    """Idempotent migrations: auth tables, user_id, complexity, reasoning."""
    is_sqlite = "sqlite" in str(engine.url)
    default_user_id = 1

    # 1. Create users table
    if not _table_exists(engine, "users"):
        logger.info("Migration: creating users table")
        _run(engine, """
            CREATE TABLE users (
                id INTEGER NOT NULL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME
            )
        """ if is_sqlite else """
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                username VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP
            )
        """)

    # 2. Insert default user if no users
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    if count == 0:
        logger.info("Migration: inserting default user (migrated@focusflow.local)")
        import bcrypt
        pwd = bcrypt.hashpw(b"changeme", bcrypt.gensalt()).decode("utf-8")
        _run(engine, f"""
            INSERT INTO users (email, username, password_hash, is_active, created_at)
            VALUES ('migrated@focusflow.local', 'migrated', '{pwd}', 1, datetime('now'))
        """ if is_sqlite else f"""
            INSERT INTO users (email, username, password_hash, is_active, created_at)
            VALUES ('migrated@focusflow.local', 'migrated', '{pwd}', TRUE, NOW())
        """)

    # 3. Create password_reset_tokens table
    if not _table_exists(engine, "password_reset_tokens"):
        logger.info("Migration: creating password_reset_tokens table")
        fk = "REFERENCES users(id) ON DELETE CASCADE"
        _run(engine, f"""
            CREATE TABLE password_reset_tokens (
                id INTEGER NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL {fk},
                token VARCHAR(255) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL,
                created_at DATETIME
            )
        """ if is_sqlite else f"""
            CREATE TABLE password_reset_tokens (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL {fk},
                token VARCHAR(255) NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP
            )
        """)

    # 4. Add user_id to tasks
    if _table_exists(engine, "tasks") and not _column_exists(engine, "tasks", "user_id"):
        logger.info("Migration: adding user_id to tasks")
        if is_sqlite:
            _run(engine, f"ALTER TABLE tasks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            _run(engine, f"UPDATE tasks SET user_id = {default_user_id} WHERE user_id IS NULL")
            _run(engine, "CREATE INDEX ix_tasks_user_id ON tasks (user_id)")
        else:
            _run(engine, f"ALTER TABLE tasks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            _run(engine, f"UPDATE tasks SET user_id = {default_user_id} WHERE user_id IS NULL")
            _run(engine, "ALTER TABLE tasks ALTER COLUMN user_id DROP DEFAULT")
            _run(engine, "ALTER TABLE tasks ADD CONSTRAINT fk_tasks_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            _run(engine, "CREATE INDEX ix_tasks_user_id ON tasks (user_id)")

    # 4b. Add complexity to tasks
    if _table_exists(engine, "tasks") and not _column_exists(engine, "tasks", "complexity"):
        logger.info("Migration: adding complexity to tasks")
        _run(engine, "ALTER TABLE tasks ADD COLUMN complexity VARCHAR(10)")

    # 4c. Add reasoning to tasks
    if _table_exists(engine, "tasks") and not _column_exists(engine, "tasks", "reasoning"):
        logger.info("Migration: adding reasoning to tasks")
        _run(engine, "ALTER TABLE tasks ADD COLUMN reasoning TEXT")

    # 5. Add user_id to schedule_blocks
    if _table_exists(engine, "schedule_blocks") and not _column_exists(engine, "schedule_blocks", "user_id"):
        logger.info("Migration: adding user_id to schedule_blocks")
        if is_sqlite:
            _run(engine, f"ALTER TABLE schedule_blocks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            _run(engine, f"UPDATE schedule_blocks SET user_id = {default_user_id} WHERE user_id IS NULL")
            _run(engine, "CREATE INDEX ix_schedule_blocks_user_id ON schedule_blocks (user_id)")
        else:
            _run(engine, f"ALTER TABLE schedule_blocks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            _run(engine, f"UPDATE schedule_blocks SET user_id = {default_user_id}")
            _run(engine, "ALTER TABLE schedule_blocks ALTER COLUMN user_id DROP DEFAULT")
            _run(engine, "ALTER TABLE schedule_blocks ADD CONSTRAINT fk_schedule_blocks_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            _run(engine, "CREATE INDEX ix_schedule_blocks_user_id ON schedule_blocks (user_id)")

    # 6. Add user_id to user_schedule_inputs
    if _table_exists(engine, "user_schedule_inputs") and not _column_exists(engine, "user_schedule_inputs", "user_id"):
        logger.info("Migration: adding user_id to user_schedule_inputs")
        if is_sqlite:
            _run(engine, f"ALTER TABLE user_schedule_inputs ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            _run(engine, f"UPDATE user_schedule_inputs SET user_id = {default_user_id} WHERE user_id IS NULL")
            _run(engine, "CREATE INDEX ix_user_schedule_inputs_user_id ON user_schedule_inputs (user_id)")
        else:
            _run(engine, f"ALTER TABLE user_schedule_inputs ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            _run(engine, f"UPDATE user_schedule_inputs SET user_id = {default_user_id}")
            _run(engine, "ALTER TABLE user_schedule_inputs ALTER COLUMN user_id DROP DEFAULT")
            _run(engine, "ALTER TABLE user_schedule_inputs ADD CONSTRAINT fk_user_schedule_inputs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            _run(engine, "CREATE INDEX ix_user_schedule_inputs_user_id ON user_schedule_inputs (user_id)")

    # 7. day_logs: add user_id and unique (user_id, date)
    if _table_exists(engine, "day_logs") and not _column_exists(engine, "day_logs", "user_id"):
        logger.info("Migration: adding user_id to day_logs")
        if is_sqlite:
            _run(engine, f"ALTER TABLE day_logs ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            _run(engine, f"UPDATE day_logs SET user_id = {default_user_id} WHERE user_id IS NULL")
            _run(engine, """
                CREATE TABLE day_logs_new (
                    id INTEGER NOT NULL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    date DATE NOT NULL,
                    content TEXT
                )
            """)
            _run(engine, "INSERT INTO day_logs_new (id, user_id, date, content) SELECT id, user_id, date, content FROM day_logs")
            _run(engine, "DROP TABLE day_logs")
            _run(engine, "ALTER TABLE day_logs_new RENAME TO day_logs")
            _run(engine, "CREATE INDEX ix_day_logs_user_id ON day_logs (user_id)")
            _run(engine, "CREATE INDEX ix_day_logs_date ON day_logs (date)")
            _run(engine, "CREATE UNIQUE INDEX uq_day_log_user_date ON day_logs (user_id, date)")
        else:
            _run(engine, f"ALTER TABLE day_logs ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            _run(engine, f"UPDATE day_logs SET user_id = {default_user_id} WHERE user_id IS NULL")
            _run(engine, "ALTER TABLE day_logs ALTER COLUMN user_id DROP DEFAULT")
            _run(engine, "ALTER TABLE day_logs ADD CONSTRAINT fk_day_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            _run(engine, "CREATE INDEX ix_day_logs_user_id ON day_logs (user_id)")
            try:
                _run(engine, "ALTER TABLE day_logs DROP CONSTRAINT IF EXISTS day_logs_date_key")
            except Exception:
                pass
            _run(engine, "CREATE UNIQUE INDEX uq_day_log_user_date ON day_logs (user_id, date)")

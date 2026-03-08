#!/usr/bin/env python3
"""
Migration: Add auth tables (users, password_reset_tokens) and user_id to
tasks, schedule_blocks, user_schedule_inputs, day_logs.
Existing rows are assigned to a default user (migrated@focusflow.local).
Run from backend dir: python -m scripts.migrate_auth
Or: python scripts/migrate_auth.py (with backend on PYTHONPATH)
"""
import os
import sys

# Load .env and ensure app is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine

# Same URL handling as app.database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./focusflow.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
if "postgresql" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL += "&sslmode=require" if "?" in DATABASE_URL else "?sslmode=require"

connect_args = {} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
is_sqlite = "sqlite" in DATABASE_URL


def table_exists(engine: Engine, name: str) -> bool:
    return name in inspect(engine).get_table_names()


def column_exists(engine: Engine, table: str, col: str) -> bool:
    return col in [c["name"] for c in inspect(engine).get_columns(table)]


def run(engine: Engine, *statements: str) -> None:
    for s in statements:
        if not s.strip():
            continue
        with engine.connect() as conn:
            conn.execute(text(s))
            conn.commit()


def migrate(engine: Engine) -> None:
    print("Checking database...")
    inspector = inspect(engine)

    # 1. Create users table
    if not table_exists(engine, "users"):
        print("Creating users table...")
        run(engine, """
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
    else:
        print("Users table already exists.")

    # 2. Insert default user if no users (for backfilling existing data)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar() or 0
    if count == 0:
        print("Inserting default migration user (migrated@focusflow.local)...")
        from passlib.context import CryptContext
        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto").hash("changeme")
        run(engine, f"""
            INSERT INTO users (email, username, password_hash, is_active, created_at)
            VALUES ('migrated@focusflow.local', 'migrated', '{pwd}', 1, datetime('now'))
        """ if is_sqlite else f"""
            INSERT INTO users (email, username, password_hash, is_active, created_at)
            VALUES ('migrated@focusflow.local', 'migrated', '{pwd}', TRUE, NOW())
        """)
    default_user_id = 1

    # 3. Create password_reset_tokens table
    if not table_exists(engine, "password_reset_tokens"):
        print("Creating password_reset_tokens table...")
        fk = "REFERENCES users(id) ON DELETE CASCADE"
        run(engine, f"""
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
    else:
        print("password_reset_tokens table already exists.")

    # 4. Add user_id to tasks
    if table_exists(engine, "tasks") and not column_exists(engine, "tasks", "user_id"):
        print("Adding user_id to tasks...")
        if is_sqlite:
            run(engine, f"ALTER TABLE tasks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            run(engine, f"UPDATE tasks SET user_id = {default_user_id} WHERE user_id IS NULL")
            run(engine, f"CREATE INDEX ix_tasks_user_id ON tasks (user_id)")
        else:
            run(engine, f"ALTER TABLE tasks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            run(engine, f"UPDATE tasks SET user_id = {default_user_id} WHERE user_id IS NULL")
            run(engine, "ALTER TABLE tasks ALTER COLUMN user_id DROP DEFAULT")
            run(engine, "ALTER TABLE tasks ADD CONSTRAINT fk_tasks_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            run(engine, "CREATE INDEX ix_tasks_user_id ON tasks (user_id)")
    elif column_exists(engine, "tasks", "user_id"):
        print("tasks.user_id already exists.")

    # 5. Add user_id to schedule_blocks
    if table_exists(engine, "schedule_blocks") and not column_exists(engine, "schedule_blocks", "user_id"):
        print("Adding user_id to schedule_blocks...")
        if is_sqlite:
            run(engine, f"ALTER TABLE schedule_blocks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            run(engine, f"UPDATE schedule_blocks SET user_id = {default_user_id} WHERE user_id IS NULL")
            run(engine, f"CREATE INDEX ix_schedule_blocks_user_id ON schedule_blocks (user_id)")
        else:
            run(engine, f"ALTER TABLE schedule_blocks ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            run(engine, f"UPDATE schedule_blocks SET user_id = {default_user_id}")
            run(engine, "ALTER TABLE schedule_blocks ALTER COLUMN user_id DROP DEFAULT")
            run(engine, "ALTER TABLE schedule_blocks ADD CONSTRAINT fk_schedule_blocks_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            run(engine, "CREATE INDEX ix_schedule_blocks_user_id ON schedule_blocks (user_id)")
    elif table_exists(engine, "schedule_blocks") and column_exists(engine, "schedule_blocks", "user_id"):
        print("schedule_blocks.user_id already exists.")

    # 6. Add user_id to user_schedule_inputs
    if table_exists(engine, "user_schedule_inputs") and not column_exists(engine, "user_schedule_inputs", "user_id"):
        print("Adding user_id to user_schedule_inputs...")
        if is_sqlite:
            run(engine, f"ALTER TABLE user_schedule_inputs ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            run(engine, f"UPDATE user_schedule_inputs SET user_id = {default_user_id} WHERE user_id IS NULL")
            run(engine, f"CREATE INDEX ix_user_schedule_inputs_user_id ON user_schedule_inputs (user_id)")
        else:
            run(engine, f"ALTER TABLE user_schedule_inputs ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
            run(engine, f"UPDATE user_schedule_inputs SET user_id = {default_user_id}")
            run(engine, "ALTER TABLE user_schedule_inputs ALTER COLUMN user_id DROP DEFAULT")
            run(engine, "ALTER TABLE user_schedule_inputs ADD CONSTRAINT fk_user_schedule_inputs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
            run(engine, "CREATE INDEX ix_user_schedule_inputs_user_id ON user_schedule_inputs (user_id)")
    elif table_exists(engine, "user_schedule_inputs") and column_exists(engine, "user_schedule_inputs", "user_id"):
        print("user_schedule_inputs.user_id already exists.")

    # 7. day_logs: add user_id and change unique to (user_id, date)
    if table_exists(engine, "day_logs"):
        if not column_exists(engine, "day_logs", "user_id"):
            print("Adding user_id to day_logs...")
            if is_sqlite:
                # SQLite: add column, backfill, then recreate table to replace date UNIQUE with (user_id, date) UNIQUE
                run(engine, f"ALTER TABLE day_logs ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
                run(engine, f"UPDATE day_logs SET user_id = {default_user_id} WHERE user_id IS NULL")
                # Recreate with correct unique constraint (SQLite doesn't allow dropping UNIQUE on column easily)
                run(engine, """
                    CREATE TABLE day_logs_new (
                        id INTEGER NOT NULL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        date DATE NOT NULL,
                        content TEXT
                    )
                """)
                run(engine, "INSERT INTO day_logs_new (id, user_id, date, content) SELECT id, user_id, date, content FROM day_logs")
                run(engine, "DROP TABLE day_logs")
                run(engine, "ALTER TABLE day_logs_new RENAME TO day_logs")
                run(engine, "CREATE INDEX ix_day_logs_user_id ON day_logs (user_id)")
                run(engine, "CREATE INDEX ix_day_logs_date ON day_logs (date)")
                run(engine, "CREATE UNIQUE INDEX uq_day_log_user_date ON day_logs (user_id, date)")
            else:
                run(engine, f"ALTER TABLE day_logs ADD COLUMN user_id INTEGER DEFAULT {default_user_id}")
                run(engine, f"UPDATE day_logs SET user_id = {default_user_id} WHERE user_id IS NULL")
                run(engine, "ALTER TABLE day_logs ALTER COLUMN user_id DROP DEFAULT")
                run(engine, "ALTER TABLE day_logs ADD CONSTRAINT fk_day_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")
                run(engine, "CREATE INDEX ix_day_logs_user_id ON day_logs (user_id)")
                # Drop old unique on date if exists, add new unique
                try:
                    run(engine, "ALTER TABLE day_logs DROP CONSTRAINT IF EXISTS day_logs_date_key")
                except Exception:
                    pass
                run(engine, "CREATE UNIQUE INDEX uq_day_log_user_date ON day_logs (user_id, date)")
        else:
            print("day_logs.user_id already exists.")
    else:
        print("day_logs table does not exist yet (will be created by app on first run).")

    print("Migration done.")


if __name__ == "__main__":
    migrate(engine)

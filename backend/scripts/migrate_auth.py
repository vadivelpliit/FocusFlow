#!/usr/bin/env python3
"""
Run migrations manually (optional). The app also runs migrations on startup.
Adds auth tables, user_id, complexity, reasoning to existing DBs.
Usage: from backend dir: python -m scripts.migrate_auth
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from app.database import engine
from app.migrate import run_migrations

if __name__ == "__main__":
    print("Running migrations...")
    run_migrations(engine)
    print("Done.")

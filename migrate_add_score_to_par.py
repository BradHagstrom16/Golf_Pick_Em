"""
Migration: Add score_to_par column to tournament_result table
==============================================================
Run this once locally and once on PythonAnywhere before deploying code changes.

Usage:
    python migrate_add_score_to_par.py
"""

import sqlite3
import os
import sys

# Default to local dev path; override with command-line argument
DB_PATH = os.path.join(os.path.dirname(__file__), 'golf_pickem.db')
if len(sys.argv) > 1:
    DB_PATH = sys.argv[1]


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(tournament_result)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'score_to_par' in columns:
        print("Column 'score_to_par' already exists. Nothing to do.")
        conn.close()
        return

    # Add the column
    cursor.execute("ALTER TABLE tournament_result ADD COLUMN score_to_par INTEGER")
    conn.commit()
    print("✅ Added 'score_to_par' column to tournament_result table.")

    # Verify
    cursor.execute("PRAGMA table_info(tournament_result)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"   Current columns: {columns}")

    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    migrate()

"""
Golf Pick 'Em - Database Migration Script
==========================================

Adds new columns for email notification tracking:
- picks_open_notified: Track if "picks are open" email was sent
- field_alert_sent: Track if admin alert was sent for missing field

Run this script ONCE on PythonAnywhere to update your database.

Usage:
    cd /home/GolfPickEm/Golf_Pick_Em
    /home/GolfPickEm/.virtualenvs/golfpickem/bin/python3 migrate_add_notification_flags.py
"""

import os
import sys

# Add project path
PROJECT_HOME = '/home/GolfPickEm/Golf_Pick_Em'
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.environ.setdefault('FLASK_ENV', 'production')

from app import app
from models import db

def run_migration():
    """Add notification tracking columns to Tournament table."""
    
    print("=" * 60)
    print("Golf Pick 'Em - Database Migration")
    print("Adding email notification tracking columns")
    print("=" * 60)
    
    with app.app_context():
        # Check current schema
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('tournament')]
        
        print(f"\nCurrent Tournament columns: {len(columns)}")
        
        migrations_needed = []
        
        if 'picks_open_notified' not in columns:
            migrations_needed.append(('picks_open_notified', 'BOOLEAN DEFAULT 0'))
        else:
            print("✓ picks_open_notified column already exists")
        
        if 'field_alert_sent' not in columns:
            migrations_needed.append(('field_alert_sent', 'BOOLEAN DEFAULT 0'))
        else:
            print("✓ field_alert_sent column already exists")
        
        if not migrations_needed:
            print("\n✅ No migrations needed - database is up to date!")
            return
        
        print(f"\n📝 Adding {len(migrations_needed)} new column(s)...")
        
        for col_name, col_def in migrations_needed:
            try:
                sql = f"ALTER TABLE tournament ADD COLUMN {col_name} {col_def}"
                db.session.execute(db.text(sql))
                print(f"   ✓ Added {col_name}")
            except Exception as e:
                if 'duplicate column name' in str(e).lower():
                    print(f"   ✓ {col_name} already exists (skipped)")
                else:
                    print(f"   ❌ Failed to add {col_name}: {e}")
                    raise
        
        db.session.commit()
        
        # Verify migration
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('tournament')]
        
        print("\n" + "=" * 60)
        print("Migration Complete!")
        print("=" * 60)
        print(f"\nVerification - Tournament columns now include:")
        for col in ['picks_open_notified', 'field_alert_sent']:
            status = "✓" if col in columns else "❌"
            print(f"   {status} {col}")
        
        print("\n📌 Next steps:")
        print("   1. Update models.py with new file")
        print("   2. Update send_reminders.py with new file")
        print("   3. Update sync_api.py with new file")
        print("   4. Reload your web app on PythonAnywhere")


if __name__ == "__main__":
    run_migration()

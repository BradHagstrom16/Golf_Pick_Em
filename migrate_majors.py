from app import app
from models import db, Tournament

with app.app_context():
    try:
        db.session.execute(db.text('ALTER TABLE tournament ADD COLUMN is_major BOOLEAN DEFAULT 0'))
        db.session.commit()
        print("Added is_major column")
    except Exception as e:
        print(f"Column may already exist: {e}")
        db.session.rollback()
    
    majors = [
        'Masters Tournament',
        'PGA Championship',
        'U.S. Open',
        'The Open Championship'
    ]
    
    for major_name in majors:
        tournament = Tournament.query.filter_by(name=major_name, season_year=2026).first()
        if tournament:
            tournament.is_major = True
            print(f"Set {major_name} as major")
        else:
            print(f"Could not find: {major_name}")
    
    db.session.commit()
    print("Database updated!")
    
    print("\n=== MAJORS ===")
    majors = Tournament.query.filter_by(is_major=True, season_year=2026).all()
    for m in majors:
        print(f"  {m.name} - {m.start_date.strftime('%B %d')}")


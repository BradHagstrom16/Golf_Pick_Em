# Golf Pick 'Em League

A season-long PGA Tour fantasy golf pick 'em game where contestants pick one golfer per tournament to earn points based on actual prize money.

## How It Works

- **Pick One Golfer Per Tournament**: Select a primary and backup golfer before each tournament deadline
- **Points = Prize Money**: Your points are the actual dollars your golfer earns
- **Use Each Golfer Once**: Once you pick a golfer, they're locked for the rest of the season
- **Backup Pick Rule**: Your backup only activates if your primary withdraws before completing Round 2

## Features

- 🏌️ 32 PGA Tour tournaments (Sony Open → BMW Championship)
- 💰 Points based on actual prize money earned
- 🔄 Primary + backup pick system
- 📊 Real-time leaderboard
- 👤 User authentication
- 🔧 Admin dashboard for tournament management
- 💳 Payment tracking

## Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/Golf_Pick_Em.git
cd Golf_Pick_Em

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
flask init-db

# Create admin user
flask create-admin

# Run development server
flask run
```

## Project Structure

```
Golf_Pick_Em/
├── app.py              # Main Flask application
├── models.py           # SQLAlchemy database models
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── templates/          # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── my_picks.html
│   ├── make_pick.html
│   ├── leaderboard.html
│   ├── schedule.html
│   └── admin/
│       ├── dashboard.html
│       ├── tournaments.html
│       ├── users.html
│       └── payments.html
└── static/
    └── css/
        └── style.css
```

## Game Rules

### Picking
- Submit primary + backup pick before first tee time Thursday
- Both picks must be from the tournament field
- Amateurs are not pickable
- Cannot reuse a golfer you've already "used"

### Backup Activation
| Scenario | Active Pick | Primary Status | Backup Status |
|----------|-------------|----------------|---------------|
| Primary finishes | Primary | Used | Unused |
| Primary WDs before R2 | Backup | Returns to pool | Used |
| Primary WDs after R2 | Primary (0 pts) | Used | Unused |
| Both WD before R2 | Primary (0 pts) | Used | Unused |

### Special Events
- **Zurich Classic (Team Event)**: Pick one player, earnings divided by 2
- **Tour Championship**: Excluded from league
- **Opposite Field Events**: Excluded (only main events count)

## API Integration

Tournament data synced from [SlashGolf API](https://slashgolf.dev/):
- Tournament schedule & purse
- Player fields
- Tee times (for deadline automation)
- Final earnings

## Environment Variables

```
FLASK_ENV=development|production
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///golf_pickem.db
SYNC_MODE=free|standard
FIXED_DEADLINE_HOUR_CT=7
```

## 2026 Tournament Schedule

32 tournaments from January (Sony Open) through August (BMW Championship).
See `/schedule` route for full list.

## PythonAnywhere Scheduled Tasks (Free Tier Mode)

Set the following scheduled tasks (replace `USER` with your PythonAnywhere username and ensure `FLASK_APP`, `SLASHGOLF_API_KEY`, and your virtualenv are configured in the task environment). Commands assume the repo lives at `/home/USER/Golf_Pick_Em`. These windows align with RapidAPI's free-tier limits (no live polling):

| Window | Frequency | Command |
| --- | --- | --- |
| Mon 07:00 CT | Weekly schedule refresh | `cd /home/USER/Golf_Pick_Em && flask sync-run --mode schedule` |
| Tue 09:00 CT | Field/roster refresh (light) | `cd /home/USER/Golf_Pick_Em && flask sync-run --mode field` |
| Wed 12:00 CT | Field/roster confirmation (optional second pass) | `cd /home/USER/Golf_Pick_Em && flask sync-run --mode field` |
| Sun 20:00 CT | Results/earnings + pick processing | `cd /home/USER/Golf_Pick_Em && flask sync-run --mode results` |
| Mon 08:00 CT | Results retry (ensures late postings) | `cd /home/USER/Golf_Pick_Em && flask sync-run --mode results` |

Live leaderboard polling and mid-round withdrawal monitoring are disabled in `SYNC_MODE=free` to stay within the RapidAPI 250 requests/month and 20 scorecards/day ceilings.

## License

Private project for personal use.

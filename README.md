# Campus Resource Hub

Campus Resource Hub is a Flask 3 application that helps students and staff discover, book, and review university resources. It supports role-aware navigation, booking approvals, threaded messaging, and an admin dashboard ready for classroom demonstrations and production deployment.

## Screens & Features
- **Authentication**: Register, login, logout with bcrypt hashing and CSRF protection.
- **Resource Listings**: CRUD for campus resources with lifecycle states (draft → published → archived).
- **Search & Filter**: Keyword, category, location, date range, and rating sorting.
- **Booking Workflow**: Conflict detection, pending/approved/completed transitions, and requester dashboard.
- **Messaging**: Threaded conversations between requesters and resource owners.
- **Reviews**: Post-booking feedback with rating aggregation.
- **Admin Panel**: Metrics, user moderation, resource archiving, and booking approvals.

## Tech Stack
- Python 3.11
- Flask, Jinja2, Flask-Login, Flask-WTF, WTForms
- SQLite (local) with optional `DATABASE_URL` override
- Bootstrap 5 professional light theme
- pytest for automated testing

## Local Setup (Windows PowerShell)
```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# env
Copy-Item .env.example .env

# initialize db
python -c "from src.data_access.db import init_db; init_db()"
python -m src.data_access.seed

# run
$env:FLASK_APP='src/app.py'
flask run
```

## Running Tests
```powershell
. .\.venv\Scripts\Activate.ps1
pytest -q
```

## Common Env Vars
- `FLASK_SECRET_KEY`
- `FLASK_ENV`
- `DATABASE_URL`

## Deployment (Render)
- `render.yaml` configures a Python web service that installs requirements and launches `gunicorn src.wsgi:app`.
- `Procfile` mirrors the Gunicorn command for local parity.
- Set `FLASK_SECRET_KEY` and `DATABASE_URL` in Render’s dashboard before deploy. If using SQLite, provide a persistent disk or switch to a managed Postgres instance.

## AI-First Development
- `.prompt/dev_notes.md` tracks prompt sessions, outcomes, and reflection on validation & ethics.
- `.prompt/golden_prompts.md` catalogs high-impact prompts; this master prompt is recorded as Golden Prompt #1.
- Comments tagged with `# AI Contribution` highlight areas where AI drafted code later reviewed by the team.

## Security Notes
- Bcrypt password hashing with unique salts.
- CSRF protection via Flask-WTF on all forms.
- Parameterized queries throughout the data access layer.
- Strict file upload validation (extension whitelist, randomized names, 2 MB limit).
- Role-based decorators guard admin-only endpoints.

## Repository Structure
```
campus_resource_hub/
├── .prompt/               # AI-first development logs
├── docs/                  # Context, OKRs, security summary
├── src/                   # Flask app (controllers, models, views, static assets)
├── tests/                 # pytest suite (auth, DAL, conflicts, search)
├── campus_resource_hub_schema.sql
├── requirements.txt
├── render.yaml
├── Procfile
└── README.md
```

## License / Academic Use
Intended for academic coursework and non-commercial classroom demonstrations. Adapt as needed for institutional policies.

## What changed in this iteration
- Added explicit admin role enforcement across dashboards, moderation, and approvals with shared `login_required` + role decorators.
- Introduced resource-level approval toggles so restricted bookings start pending, include notes, and surface in staff/admin queues.
- Rebuilt messaging into threads with admin inbox views, contextual routing, and 6-second polling for near-real-time updates.
- Replaced all remote imagery with local SVG placeholders and refreshed Bootstrap 5 light-mode spacing, badges, and focus states.
- Updated database schema (threads, approval notes, flags) – run `flask --app src.app init-db` then `python -m src.data_access.seed` to re-initialize locally when migrating existing SQLite files.
- Seeded 1 admin, 2 staff, and 3 students with sample resources, bookings, and conversations for quick end-to-end testing.


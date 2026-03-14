# מתכונים — Recipes Web App

A simple Hebrew (RTL) recipes web app built with Python, Flask, and SQLite.

## Features

- Browse and search recipes (by title, ingredients, instructions, or tags)
- Add, edit, and delete recipes (admin)
- Upload multiple images per recipe with inline placement via `[תמונה N]` placeholders
- Upload and play videos directly in the recipe page
- Tag system with filtering
- Comments on recipes (deletable by admin)
- Anonymous like / dislike voting with net score
- Fully Hebrew UI with RTL layout

---

## Quick Start

### One-command startup (recommended)

The startup scripts handle everything automatically: they check for Python 3,
create the virtual environment, install dependencies, create required directories,
initialise the database, and launch the app.

**macOS / Linux**

```bash
./start.sh
```

> If the script is not yet executable, run `chmod +x start.sh` first.

**Windows (CMD or PowerShell)**

```bat
start.bat
```

> You can also double-click `start.bat` in Explorer.

**Windows (Git Bash / WSL)**

```bash
./start.sh
```

What the scripts do, in order:

| Step | Action |
|---|---|
| 1 | Detect the operating system |
| 2 | Find Python 3.10+ — install it automatically if missing |
| 3 | Create `venv/` virtual environment if it does not exist |
| 4 | Install / upgrade all dependencies from `requirements.txt` |
| 5 | Create `static/uploads`, `static/videos`, and `instance/` if missing |
| 6 | Run `init_db.py` to create database tables if `recipes.db` does not exist |
| 7 | Start the app on http://localhost:5000 |

Every step is idempotent — already-existing resources are left untouched.

---

### Manual setup (alternative)

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database tables
python init_db.py

# 4. Run the development server
python app.py
```

Then open http://localhost:5000 in your browser.

---

## Admin Panel

Navigate to http://localhost:5000/admin/login

Default credentials (change via environment variables before deploying):

| Variable | Default |
|---|---|
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_PASSWORD` | `admin123` |

---

## Configuration

All settings live in `config.py` and can be overridden with environment variables:

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing key | `change-me-in-production` |
| `ADMIN_USERNAME` | Admin login username | `admin` |
| `ADMIN_PASSWORD` | Admin login password | `admin123` |
| `DATABASE_URL` | SQLAlchemy database URI | `sqlite:///recipes.db` |

---

## Running Tests

```bash
# With the venv active:
pytest tests.py -v

# Or directly:
venv/bin/pytest tests.py -v      # macOS / Linux
venv\Scripts\pytest tests.py -v  # Windows
```

70 tests covering all public routes, admin CRUD, votes, images, and videos.

---

## Project Layout

```
start.sh        — Startup script (macOS / Linux / Git Bash)
start.bat       — Startup script (Windows CMD / PowerShell)
app.py          — All routes (single file)
models.py       — SQLAlchemy models
config.py       — Configuration
init_db.py      — Create database tables
tests.py        — Test suite
requirements.txt
static/
  css/style.css — Custom styles (RTL, Heebo font)
  uploads/      — Uploaded recipe images
  videos/       — Uploaded recipe videos
templates/
  base.html               — RTL base layout (Bootstrap 5 RTL)
  index.html              — Recipe list / homepage
  recipe.html             — Single recipe view
  recipe_form.html        — Add / edit recipe form
  search.html             — Search results
  404.html / 500.html     — Error pages
  admin/
    login.html            — Admin login
    dashboard.html        — Admin overview
    recipes.html          — Manage recipes
    tags.html             — Manage tags
    comments.html         — Manage comments
```

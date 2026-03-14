# מתכונים — Recipes Web App

A simple Hebrew (RTL) recipes web app built with Python, Flask, and SQLite.

## Features

- Browse and search recipes (by title, body, or tags)
- Add, edit, and delete recipes (admin)
- Upload multiple images per recipe (gallery or inline)
- Tag system with filtering
- Comments on recipes (deletable by admin)
- Fully Hebrew UI with RTL layout

## Quick Start

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database tables
python init_db.py

# 4. Run the development server
python app.py
```

Then open http://localhost:5000 in your browser.

## Admin Panel

Navigate to http://localhost:5000/admin/login

Default credentials (change via environment variables before deploying):

| Variable | Default |
|---|---|
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_PASSWORD` | `admin123` |

## Configuration

All configuration is in `config.py` and can be overridden with environment variables:

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Flask session signing key | `change-me-in-production` |
| `ADMIN_USERNAME` | Admin login username | `admin` |
| `ADMIN_PASSWORD` | Admin login password | `admin123` |
| `DATABASE_URL` | SQLAlchemy database URI | `sqlite:///recipes.db` |

## Running Tests

```bash
pytest tests.py -v
```

56 tests covering all public and admin endpoints.

## Project Layout

```
app.py          — All routes (single file)
models.py       — SQLAlchemy models
config.py       — Configuration
init_db.py      — Create database tables
tests.py        — Test suite
static/
  css/style.css — Custom styles
  uploads/      — Uploaded recipe images
templates/
  base.html               — RTL base layout
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

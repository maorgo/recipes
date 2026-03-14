# Design: Hebrew Recipes Web App

## 1. Project Structure

```
receips/
├── app.py                  # Main Flask application & routes
├── models.py               # SQLAlchemy models
├── config.py               # Configuration
├── requirements.txt        # Dependencies
├── init_db.py              # Database initialization script
├── static/
│   ├── css/
│   │   └── style.css       # Custom styles (RTL, Hebrew fonts)
│   └── uploads/            # Uploaded recipe images
├── templates/
│   ├── base.html           # Base layout (RTL, nav, flash messages)
│   ├── index.html          # Homepage – recipe list
│   ├── recipe.html         # Single recipe view (with comments)
│   ├── recipe_form.html    # Add/Edit recipe form
│   ├── search.html         # Search results
│   └── admin/
│       ├── dashboard.html  # Admin panel overview
│       ├── recipes.html    # Manage recipes
│       ├── tags.html       # Manage tags
│       └── comments.html   # Manage comments
└── README.md
```

**Philosophy:** Keep everything flat and minimal. No blueprints, no complex folder nesting. One `app.py` with all routes, one `models.py` with all models.

---

## 2. Data Model (SQLite via SQLAlchemy)

### Tables

**recipes**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| title | TEXT | Required, indexed for search |
| body | TEXT | Recipe content (HTML or Markdown) |
| created_at | DATETIME | Default now |
| updated_at | DATETIME | Auto-update |

**tags**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| name | TEXT | Unique, Hebrew tag name |

**recipe_tags** (association table)
| Column | Type | Notes |
|---|---|---|
| recipe_id | FK → recipes.id | |
| tag_id | FK → tags.id | |

**images**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| recipe_id | FK → recipes.id | |
| filename | TEXT | Stored filename |
| position | TEXT | `"inline"` or `"gallery"` (end of post) |
| sort_order | INTEGER | Display ordering |

**comments**
| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | Auto-increment |
| recipe_id | FK → recipes.id | |
| author_name | TEXT | Commenter's name |
| body | TEXT | Comment text |
| created_at | DATETIME | Default now |

### Relationships
- Recipe → many Images (cascade delete)
- Recipe → many Comments (cascade delete)
- Recipe ↔ many Tags (many-to-many via `recipe_tags`)

---

## 3. Routes / Endpoints

### Public Routes

| Method | Path | Description |
|---|---|---|
| GET | `/` | Homepage – list all recipes (paginated, newest first) |
| GET | `/recipe/<id>` | View single recipe with images & comments |
| POST | `/recipe/<id>/comment` | Add a comment to a recipe |
| GET | `/search?q=...` | Search recipes by title, body, or tags |
| GET | `/tag/<id>` | List recipes with a specific tag |

### Admin Routes (password-protected)

| Method | Path | Description |
|---|---|---|
| GET | `/admin/login` | Login page |
| POST | `/admin/login` | Authenticate admin |
| GET | `/admin/logout` | Logout |
| GET | `/admin/` | Dashboard |
| GET/POST | `/admin/recipe/new` | Create recipe |
| GET/POST | `/admin/recipe/<id>/edit` | Edit recipe |
| POST | `/admin/recipe/<id>/delete` | Delete recipe |
| GET/POST | `/admin/tags` | List & create tags |
| POST | `/admin/tag/<id>/delete` | Delete tag |
| GET | `/admin/comments` | List all comments |
| POST | `/admin/comment/<id>/delete` | Delete comment |

---

## 4. Authentication (Simplest Approach)

Since this is a simple app with a single admin:

- Store admin password as a hashed value in `config.py` (or environment variable)
- Use Flask's `session` for login state
- A simple decorator `@admin_required` to protect admin routes
- No user registration — just one admin account

```python
from functools import wraps
from flask import session, redirect, url_for

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated
```

---

## 5. Search Implementation

Use SQLite's built-in `LIKE` for simplicity:

```python
@app.route('/search')
def search():
    q = request.args.get('q', '')
    pattern = f'%{q}%'
    recipes = Recipe.query.filter(
        db.or_(
            Recipe.title.ilike(pattern),
            Recipe.body.ilike(pattern),
            Recipe.tags.any(Tag.name.ilike(pattern))
        )
    ).all()
    return render_template('search.html', recipes=recipes, query=q)
```

This is sufficient for a small-to-medium recipe collection. If it grows large, SQLite FTS5 can be added later without architectural changes.

---

## 6. Image Handling

- Images uploaded via the recipe form (multipart)
- Stored on disk in `static/uploads/` with UUID-based filenames to avoid collisions
- The `images` table tracks which recipe they belong to and their position
- In the recipe form, allow marking images as "inline" (shown within the body) or "gallery" (shown at the end)
- On recipe delete, cascade-delete image records and remove files from disk

```python
import uuid
from werkzeug.utils import secure_filename

def save_image(file):
    ext = file.filename.rsplit('.', 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return filename
```

---

## 7. RTL & Hebrew Support

### Base Template (`base.html`)

```html
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}מתכונים{% endblock %}</title>
    <link rel="stylesheet"
          href="https://cdn.jsdelivr.net/npm/bootstrap@5.3/dist/css/bootstrap.rtl.min.css">
    <link rel="stylesheet"
          href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">מתכונים</a>
        </div>
    </nav>
    <main class="container my-4">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for msg in messages %}
                <div class="alert alert-info">{{ msg }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </main>
</body>
</html>
```

Key RTL decisions:
- Use **Bootstrap 5 RTL build** — gives RTL-aware grid, forms, nav, cards out of the box
- Set `dir="rtl"` and `lang="he"` on `<html>`
- All UI text (buttons, labels, navigation, flash messages) in Hebrew
- Custom CSS for Hebrew-friendly font (e.g., system Hebrew fonts or Google Fonts `Heebo`)

---

## 8. Dependencies (`requirements.txt`)

```
Flask==3.1.*
Flask-SQLAlchemy==3.1.*
Werkzeug==3.1.*
```

Minimal dependencies. No WTForms, Flask-Login, or other extras for an app this simple.

---

## 9. Implementation Order (Suggested Phases)

### Phase 1 — Foundation
1. Set up `config.py`, `app.py`, `models.py`
2. Create database schema and `init_db.py`
3. Build `base.html` with RTL + Bootstrap RTL
4. Implement admin login/logout

### Phase 2 — Recipe CRUD
5. Admin: create recipe form (title, body, tags, images)
6. Admin: edit recipe, delete recipe
7. Public: recipe list page (homepage)
8. Public: single recipe view

### Phase 3 — Tags & Images
9. Admin: tag management (list, add, delete)
10. Image upload in recipe form, gallery display
11. Tag filtering (click a tag → see related recipes)

### Phase 4 — Comments & Search
12. Comment form on recipe page
13. Admin: comment management (list, delete)
14. Search functionality

### Phase 5 — Polish
15. Pagination on recipe list
16. Flash messages in Hebrew for all actions
17. Mobile responsiveness testing
18. Basic error pages (404, 500) in Hebrew

---

## 10. Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| No blueprints | Single-file routes are easier to maintain for a small app |
| No WTForms | HTML forms + manual validation is simpler for ~4 forms |
| No Flask-Login | Session-based auth with one admin is 10 lines of code |
| SQLAlchemy (not raw SQL) | Slightly more code, but much easier to maintain models |
| Bootstrap RTL | RTL layout for free, no custom CSS gymnastics |
| Disk-based image storage | No cloud dependencies, simple `static/uploads/` folder |
| SQLite LIKE search | Good enough for hundreds/low-thousands of recipes |
| No JavaScript framework | Server-rendered HTML, zero JS complexity |

---

## 11. Hebrew UI Strings Reference

Key labels to use throughout templates:

| English | Hebrew |
|---|---|
| Recipes | מתכונים |
| Add Recipe | הוספת מתכון |
| Edit Recipe | עריכת מתכון |
| Delete | מחיקה |
| Search | חיפוש |
| Tags | תגיות |
| Comments | תגובות |
| Submit | שליחה |
| Cancel | ביטול |
| Admin Panel | פאנל ניהול |
| Login | כניסה |
| Logout | יציאה |
| Title | כותרת |
| Content | תוכן |
| Images | תמונות |
| Name | שם |
| Save | שמירה |
| Are you sure? | ?האם את/ה בטוח/ה |
| No results found | לא נמצאו תוצאות |

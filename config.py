import os

# Secret key for session signing — change this in production
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

# Admin credentials — set ADMIN_PASSWORD env var in production
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Goaz7567")

# Where to store the SQLite database
DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///recipes.db")

# Where uploaded images are saved (relative to project root)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")

# Where uploaded videos are saved (relative to project root)
VIDEO_FOLDER = os.path.join(os.path.dirname(__file__), "static", "videos")

# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Allowed video extensions
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "webm", "ogg", "mov"}

# Recipes per page on the homepage
RECIPES_PER_PAGE = 12

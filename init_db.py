"""
Run this script once to create all database tables.

    python init_db.py
"""
from app import app, db

with app.app_context():
    db.create_all()
    print("Database tables created.")

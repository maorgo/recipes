from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Association table for the many-to-many relationship between recipes and tags
recipe_tags = db.Table(
    "recipe_tags",
    db.Column("recipe_id", db.Integer, db.ForeignKey("recipes.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class Recipe(db.Model):
    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    ingredients = db.Column(db.Text, nullable=False, default="")
    instructions = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    tags = db.relationship("Tag", secondary=recipe_tags, back_populates="recipes")
    images = db.relationship(
        "Image", back_populates="recipe", cascade="all, delete-orphan", order_by="Image.sort_order"
    )
    comments = db.relationship(
        "Comment", back_populates="recipe", cascade="all, delete-orphan", order_by="Comment.created_at"
    )
    votes = db.relationship(
        "Vote", back_populates="recipe", cascade="all, delete-orphan"
    )
    videos = db.relationship(
        "Video", back_populates="recipe", cascade="all, delete-orphan", order_by="Video.sort_order"
    )


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)

    recipes = db.relationship("Recipe", secondary=recipe_tags, back_populates="tags")


class Image(db.Model):
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    filename = db.Column(db.Text, nullable=False)
    # "gallery" = shown at the end of the recipe; "inline" = referenced inside body
    position = db.Column(db.Text, nullable=False, default="gallery")
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    recipe = db.relationship("Recipe", back_populates="images")


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    author_name = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    recipe = db.relationship("Recipe", back_populates="comments")


class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    # Visitor identified by a browser cookie (anonymous, no login needed)
    visitor_id = db.Column(db.Text, nullable=False)
    # +1 for like, -1 for dislike
    value = db.Column(db.Integer, nullable=False)

    recipe = db.relationship("Recipe", back_populates="votes")
    __table_args__ = (
        db.UniqueConstraint("recipe_id", "visitor_id", name="uq_vote_per_visitor"),
    )


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    filename = db.Column(db.Text, nullable=False)
    # Original name shown to visitors (e.g. "הדגמת קיפול הבצק")
    title = db.Column(db.Text, nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    recipe = db.relationship("Recipe", back_populates="videos")

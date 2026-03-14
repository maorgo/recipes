import os
import re
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from markupsafe import Markup, escape

import config
from models import Comment, Image, Recipe, Tag, Video, Vote, db

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = config.DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
app.config["VIDEO_FOLDER"] = config.VIDEO_FOLDER

db.init_app(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS
    )


def _save_image(file):
    """Save an uploaded image and return its stored filename."""
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


def _delete_image_file(filename):
    """Remove an image file from disk if it exists."""
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(path):
        os.remove(path)


def _allowed_video(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_VIDEO_EXTENSIONS
    )


def _save_video(file):
    """Save an uploaded video file and return its stored filename."""
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(app.config["VIDEO_FOLDER"], exist_ok=True)
    file.save(os.path.join(app.config["VIDEO_FOLDER"], filename))
    return filename


def _delete_video_file(filename):
    """Remove a video file from disk if it exists."""
    path = os.path.join(app.config["VIDEO_FOLDER"], filename)
    if os.path.exists(path):
        os.remove(path)


def _render_instructions(text, images):
    """Replace [תמונה N] placeholders in text with actual <img> tags.

    images is the ordered list of Image objects for the recipe.
    Images are 1-indexed in the placeholder (e.g. [תמונה 1] = images[0]).
    Any image without a placeholder is appended at the end.
    """
    used_indices = set()

    def replace_placeholder(match):
        n = int(match.group(1))
        idx = n - 1
        if 0 <= idx < len(images):
            used_indices.add(idx)
            img = images[idx]
            img_url = url_for("static", filename=f"uploads/{img.filename}")
            return (
                f'<a href="{img_url}" target="_blank">'
                f'<img src="{img_url}" class="img-fluid rounded shadow-sm my-2" '
                f'alt="תמונה {n}" style="max-width:100%;">'
                f'</a>'
            )
        return match.group(0)  # leave unknown placeholders as-is

    # Escape user text first, then replace newlines and placeholders
    safe_text = str(escape(text))
    safe_text = safe_text.replace("\n", "<br>")
    rendered = re.sub(r'\[תמונה (\d+)\]', replace_placeholder, safe_text)

    # Append any images that had no placeholder
    extra_parts = []
    for i, img in enumerate(images):
        if i not in used_indices:
            img_url = url_for("static", filename=f"uploads/{img.filename}")
            extra_parts.append(
                f'<a href="{img_url}" target="_blank">'
                f'<img src="{img_url}" class="img-fluid rounded shadow-sm my-2" '
                f'alt="תמונה {i+1}" style="max-width:100%;">'
                f'</a>'
            )
    if extra_parts:
        rendered += "<br>" + "<br>".join(extra_parts)

    return Markup(rendered)


def admin_required(f):
    """Decorator that redirects to the login page if the user is not an admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


def _get_visitor_id():
    """Return a stable anonymous visitor ID stored in a cookie."""
    return request.cookies.get("visitor_id") or uuid.uuid4().hex


def _set_visitor_cookie(response, visitor_id):
    """Attach the visitor_id cookie to a response (1 year expiry)."""
    response.set_cookie("visitor_id", visitor_id, max_age=365 * 24 * 3600, samesite="Lax")


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = (
        Recipe.query.order_by(Recipe.created_at.desc())
        .paginate(page=page, per_page=config.RECIPES_PER_PAGE, error_out=False)
    )
    return render_template("index.html", pagination=pagination)


@app.route("/recipe/<int:recipe_id>")
def recipe(recipe_id):
    r = db.get_or_404(Recipe, recipe_id)
    rendered_instructions = _render_instructions(r.instructions, r.images)
    visitor_id = _get_visitor_id()
    visitor_vote = Vote.query.filter_by(recipe_id=r.id, visitor_id=visitor_id).first()
    score = sum(v.value for v in r.votes)
    resp = make_response(render_template(
        "recipe.html",
        recipe=r,
        rendered_instructions=rendered_instructions,
        score=score,
        visitor_vote=visitor_vote.value if visitor_vote else 0,
    ))
    _set_visitor_cookie(resp, visitor_id)
    return resp


@app.route("/recipe/<int:recipe_id>/comment", methods=["POST"])
def add_comment(recipe_id):
    r = db.get_or_404(Recipe, recipe_id)
    author = request.form.get("author_name", "").strip()
    body = request.form.get("body", "").strip()
    if not author or not body:
        flash("נא למלא את כל השדות")
        return redirect(url_for("recipe", recipe_id=r.id))
    comment = Comment(recipe_id=r.id, author_name=author, body=body)
    db.session.add(comment)
    db.session.commit()
    flash("התגובה נוספה בהצלחה")
    return redirect(url_for("recipe", recipe_id=r.id))


@app.route("/recipe/<int:recipe_id>/vote", methods=["POST"])
def vote(recipe_id):
    """Cast or retract a like (+1) / dislike (-1) vote.

    Voting the same value twice retracts the vote. Voting the opposite
    value switches it. One vote per anonymous visitor (cookie-based).
    """
    r = db.get_or_404(Recipe, recipe_id)
    value = request.form.get("value", "")
    if value not in ("1", "-1"):
        abort(400)
    value = int(value)

    visitor_id = _get_visitor_id()
    existing = Vote.query.filter_by(recipe_id=r.id, visitor_id=visitor_id).first()

    if existing:
        if existing.value == value:
            # Same button clicked again — retract
            db.session.delete(existing)
        else:
            # Opposite button — switch vote
            existing.value = value
    else:
        db.session.add(Vote(recipe_id=r.id, visitor_id=visitor_id, value=value))

    db.session.commit()

    resp = make_response(redirect(url_for("recipe", recipe_id=r.id) + "#votes"))
    _set_visitor_cookie(resp, visitor_id)
    return resp


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    recipes = []
    if q:
        pattern = f"%{q}%"
        recipes = (
            Recipe.query.filter(
                db.or_(
                    Recipe.title.ilike(pattern),
                    Recipe.ingredients.ilike(pattern),
                    Recipe.instructions.ilike(pattern),
                    Recipe.tags.any(Tag.name.ilike(pattern)),
                )
            )
            .order_by(Recipe.created_at.desc())
            .all()
        )
    return render_template("search.html", recipes=recipes, query=q)


@app.route("/tag/<int:tag_id>")
def tag(tag_id):
    t = db.get_or_404(Tag, tag_id)
    recipes = (
        Recipe.query.filter(Recipe.tags.any(Tag.id == t.id))
        .order_by(Recipe.created_at.desc())
        .all()
    )
    return render_template("index.html", pagination=None, recipes=recipes, current_tag=t)


# ---------------------------------------------------------------------------
# Admin — auth
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("שם משתמש או סיסמה שגויים")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.pop("is_admin", None)
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Admin — dashboard
# ---------------------------------------------------------------------------

@app.route("/admin/")
@admin_required
def admin_dashboard():
    recipe_count = Recipe.query.count()
    comment_count = Comment.query.count()
    tag_count = Tag.query.count()
    return render_template(
        "admin/dashboard.html",
        recipe_count=recipe_count,
        comment_count=comment_count,
        tag_count=tag_count,
    )


# ---------------------------------------------------------------------------
# Admin — recipes
# ---------------------------------------------------------------------------

@app.route("/admin/recipes")
@admin_required
def admin_recipes():
    recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
    return render_template("admin/recipes.html", recipes=recipes)


@app.route("/admin/recipe/new", methods=["GET", "POST"])
@admin_required
def admin_recipe_new():
    all_tags = Tag.query.order_by(Tag.name).all()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        ingredients = request.form.get("ingredients", "").strip()
        instructions = request.form.get("instructions", "").strip()
        if not title:
            flash("כותרת היא שדה חובה")
            return render_template("recipe_form.html", all_tags=all_tags, recipe=None)

        recipe = Recipe(title=title, ingredients=ingredients, instructions=instructions)

        # Attach selected tags
        tag_ids = request.form.getlist("tag_ids")
        for tid in tag_ids:
            t = db.session.get(Tag, int(tid))
            if t:
                recipe.tags.append(t)

        db.session.add(recipe)
        db.session.flush()  # get recipe.id before saving images

        # Handle uploaded images
        files = request.files.getlist("images")
        for i, f in enumerate(files):
            if f and f.filename and _allowed_file(f.filename):
                filename = _save_image(f)
                position = request.form.get(f"position_{i}", "gallery")
                img = Image(recipe_id=recipe.id, filename=filename, position=position, sort_order=i)
                db.session.add(img)

        # Handle uploaded videos
        video_files = request.files.getlist("videos")
        video_titles = request.form.getlist("video_titles")
        for i, f in enumerate(video_files):
            if f and f.filename and _allowed_video(f.filename):
                filename = _save_video(f)
                vtitle = video_titles[i].strip() if i < len(video_titles) else ""
                vid = Video(recipe_id=recipe.id, filename=filename, title=vtitle, sort_order=i)
                db.session.add(vid)

        db.session.commit()
        flash("המתכון נוסף בהצלחה")
        return redirect(url_for("admin_recipes"))

    return render_template("recipe_form.html", all_tags=all_tags, recipe=None)


@app.route("/admin/recipe/<int:recipe_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_recipe_edit(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    all_tags = Tag.query.order_by(Tag.name).all()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        ingredients = request.form.get("ingredients", "").strip()
        instructions = request.form.get("instructions", "").strip()
        if not title:
            flash("כותרת היא שדה חובה")
            return render_template("recipe_form.html", all_tags=all_tags, recipe=recipe)

        recipe.title = title
        recipe.ingredients = ingredients
        recipe.instructions = instructions
        recipe.updated_at = datetime.now(timezone.utc)

        # Replace tags
        recipe.tags = []
        tag_ids = request.form.getlist("tag_ids")
        for tid in tag_ids:
            t = db.session.get(Tag, int(tid))
            if t:
                recipe.tags.append(t)

        # Handle newly uploaded images
        files = request.files.getlist("images")
        existing_count = len(recipe.images)
        for i, f in enumerate(files):
            if f and f.filename and _allowed_file(f.filename):
                filename = _save_image(f)
                position = request.form.get(f"position_{i}", "gallery")
                img = Image(
                    recipe_id=recipe.id,
                    filename=filename,
                    position=position,
                    sort_order=existing_count + i,
                )
                db.session.add(img)

        # Handle image deletions
        delete_image_ids = request.form.getlist("delete_image_ids")
        for img_id in delete_image_ids:
            img = db.session.get(Image, int(img_id))
            if img and img.recipe_id == recipe.id:
                _delete_image_file(img.filename)
                db.session.delete(img)

        # Handle newly uploaded videos
        video_files = request.files.getlist("videos")
        video_titles = request.form.getlist("video_titles")
        existing_video_count = len(recipe.videos)
        for i, f in enumerate(video_files):
            if f and f.filename and _allowed_video(f.filename):
                filename = _save_video(f)
                vtitle = video_titles[i].strip() if i < len(video_titles) else ""
                vid = Video(
                    recipe_id=recipe.id,
                    filename=filename,
                    title=vtitle,
                    sort_order=existing_video_count + i,
                )
                db.session.add(vid)

        # Handle video deletions
        delete_video_ids = request.form.getlist("delete_video_ids")
        for vid_id in delete_video_ids:
            vid = db.session.get(Video, int(vid_id))
            if vid and vid.recipe_id == recipe.id:
                _delete_video_file(vid.filename)
                db.session.delete(vid)

        db.session.commit()
        flash("המתכון עודכן בהצלחה")
        return redirect(url_for("admin_recipes"))

    return render_template("recipe_form.html", all_tags=all_tags, recipe=recipe)


@app.route("/admin/recipe/<int:recipe_id>/delete", methods=["POST"])
@admin_required
def admin_recipe_delete(recipe_id):
    recipe = db.get_or_404(Recipe, recipe_id)
    for img in recipe.images:
        _delete_image_file(img.filename)
    for vid in recipe.videos:
        _delete_video_file(vid.filename)
    db.session.delete(recipe)
    db.session.commit()
    flash("המתכון נמחק")
    return redirect(url_for("admin_recipes"))


# ---------------------------------------------------------------------------
# Admin — tags
# ---------------------------------------------------------------------------

@app.route("/admin/tags", methods=["GET", "POST"])
@admin_required
def admin_tags():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("שם התגית הוא שדה חובה")
        elif Tag.query.filter_by(name=name).first():
            flash("תגית בשם זה כבר קיימת")
        else:
            db.session.add(Tag(name=name))
            db.session.commit()
            flash("התגית נוספה בהצלחה")
    tags = Tag.query.order_by(Tag.name).all()
    return render_template("admin/tags.html", tags=tags)


@app.route("/admin/tag/<int:tag_id>/delete", methods=["POST"])
@admin_required
def admin_tag_delete(tag_id):
    tag = db.get_or_404(Tag, tag_id)
    db.session.delete(tag)
    db.session.commit()
    flash("התגית נמחקה")
    return redirect(url_for("admin_tags"))


# ---------------------------------------------------------------------------
# Admin — comments
# ---------------------------------------------------------------------------

@app.route("/admin/comments")
@admin_required
def admin_comments():
    comments = Comment.query.order_by(Comment.created_at.desc()).all()
    return render_template("admin/comments.html", comments=comments)


@app.route("/admin/comment/<int:comment_id>/delete", methods=["POST"])
@admin_required
def admin_comment_delete(comment_id):
    comment = db.get_or_404(Comment, comment_id)
    db.session.delete(comment)
    db.session.commit()
    flash("התגובה נמחקה")
    return redirect(url_for("admin_comments"))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


# ---------------------------------------------------------------------------
# Template context
# ---------------------------------------------------------------------------

@app.context_processor
def inject_now():
    return {"now": datetime.now(timezone.utc)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

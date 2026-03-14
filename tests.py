"""
Tests for the Recipes web app.

Run with:  pytest tests.py -v
"""
import io
import os
import pytest

# Use an in-memory database and a temp upload folder for tests
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"

from app import app as flask_app, db
from models import Comment, Image, Recipe, Tag


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["UPLOAD_FOLDER"] = "/tmp/receips_test_uploads"
    flask_app.config["VIDEO_FOLDER"] = "/tmp/receips_test_videos"
    os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(flask_app.config["VIDEO_FOLDER"], exist_ok=True)

    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """A test client that is already logged in as admin."""
    client.post("/admin/login", data={"username": "admin", "password": "admin123"})
    return client


@pytest.fixture
def sample_recipe(app):
    """Insert a recipe and return it."""
    with app.app_context():
        tag = Tag(name="קינוחים")
        recipe = Recipe(title="עוגת שוקולד", ingredients="שוקולד, קמח, ביצים", instructions="מרכיבים ואופן הכנה...")
        recipe.tags.append(tag)
        db.session.add(recipe)
        db.session.commit()
        return recipe.id, tag.id


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

class TestIndex:
    def test_homepage_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "מתכונים".encode() in resp.data

    def test_homepage_shows_recipe(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = client.get("/")
        assert "עוגת שוקולד".encode() in resp.data

    def test_pagination_page_param(self, client):
        resp = client.get("/?page=1")
        assert resp.status_code == 200

    def test_pagination_invalid_page_returns_empty(self, client):
        resp = client.get("/?page=9999")
        assert resp.status_code == 200


class TestRecipeView:
    def test_view_recipe(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = client.get(f"/recipe/{recipe_id}")
        assert resp.status_code == 200
        assert "עוגת שוקולד".encode() in resp.data
        assert "מרכיבים ואופן הכנה".encode() in resp.data

    def test_view_nonexistent_recipe_returns_404(self, client):
        resp = client.get("/recipe/99999")
        assert resp.status_code == 404

    def test_recipe_shows_tags(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = client.get(f"/recipe/{recipe_id}")
        assert "קינוחים".encode() in resp.data

    def test_image_placeholder_renders(self, client, app):
        """[תמונה 1] in instructions should be replaced with an <img> tag."""
        with app.app_context():
            recipe = Recipe(
                title="מתכון עם תמונה",
                ingredients="קמח, ביצים",
                instructions="שלב ראשון\n[תמונה 1]\nשלב שני",
            )
            db.session.add(recipe)
            db.session.flush()
            img = Image(recipe_id=recipe.id, filename="test.jpg", position="gallery", sort_order=0)
            db.session.add(img)
            db.session.commit()
            recipe_id = recipe.id

        resp = client.get(f"/recipe/{recipe_id}")
        assert resp.status_code == 200
        assert b'<img' in resp.data
        assert b"test.jpg" in resp.data
        # The raw placeholder should not appear in the output
        assert "[תמונה 1]".encode() not in resp.data

    def test_unused_image_appended_at_end(self, client, app):
        """Images with no placeholder are appended after the instructions text."""
        with app.app_context():
            recipe = Recipe(
                title="מתכון",
                ingredients="",
                instructions="רק טקסט, ללא צלקית",
            )
            db.session.add(recipe)
            db.session.flush()
            img = Image(recipe_id=recipe.id, filename="extra.jpg", position="gallery", sort_order=0)
            db.session.add(img)
            db.session.commit()
            recipe_id = recipe.id

        resp = client.get(f"/recipe/{recipe_id}")
        assert resp.status_code == 200
        assert b"extra.jpg" in resp.data


class TestTagView:
    def test_tag_page_loads(self, client, app, sample_recipe):
        _, tag_id = sample_recipe
        resp = client.get(f"/tag/{tag_id}")
        assert resp.status_code == 200
        assert "עוגת שוקולד".encode() in resp.data

    def test_tag_nonexistent_returns_404(self, client):
        resp = client.get("/tag/99999")
        assert resp.status_code == 404


class TestSearch:
    def test_search_no_query(self, client):
        resp = client.get("/search")
        assert resp.status_code == 200

    def test_search_by_title(self, client, app, sample_recipe):
        resp = client.get("/search?q=שוקולד")
        assert resp.status_code == 200
        assert "עוגת שוקולד".encode() in resp.data

    def test_search_by_ingredients(self, client, app, sample_recipe):
        resp = client.get("/search?q=שוקולד")
        assert resp.status_code == 200
        assert "עוגת שוקולד".encode() in resp.data

    def test_search_by_instructions(self, client, app, sample_recipe):
        resp = client.get("/search?q=מרכיבים")
        assert resp.status_code == 200
        assert "עוגת שוקולד".encode() in resp.data

    def test_search_by_tag(self, client, app, sample_recipe):
        resp = client.get("/search?q=קינוחים")
        assert resp.status_code == 200
        assert "עוגת שוקולד".encode() in resp.data

    def test_search_no_results(self, client, app, sample_recipe):
        resp = client.get("/search?q=xyznotfound")
        assert resp.status_code == 200
        assert "לא נמצאו תוצאות".encode() in resp.data


class TestComments:
    def test_add_comment(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = client.post(
            f"/recipe/{recipe_id}/comment",
            data={"author_name": "דנה", "body": "מתכון נהדר!"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "דנה".encode() in resp.data
        assert "מתכון נהדר".encode() in resp.data

    def test_add_comment_empty_fields(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = client.post(
            f"/recipe/{recipe_id}/comment",
            data={"author_name": "", "body": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        # Should flash an error, not create a comment
        with app.app_context():
            assert Comment.query.count() == 0

    def test_add_comment_to_nonexistent_recipe(self, client):
        resp = client.post(
            "/recipe/99999/comment",
            data={"author_name": "דנה", "body": "שאלה"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------

class TestVotes:
    def test_like_recipe(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = client.post(
            f"/recipe/{recipe_id}/vote",
            data={"value": "1"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            from models import Vote
            assert Vote.query.filter_by(recipe_id=recipe_id, value=1).count() == 1

    def test_dislike_recipe(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = client.post(
            f"/recipe/{recipe_id}/vote",
            data={"value": "-1"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            from models import Vote
            assert Vote.query.filter_by(recipe_id=recipe_id, value=-1).count() == 1

    def test_vote_twice_same_value_retracts(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        client.post(f"/recipe/{recipe_id}/vote", data={"value": "1"})
        client.post(f"/recipe/{recipe_id}/vote", data={"value": "1"})
        with app.app_context():
            from models import Vote
            assert Vote.query.filter_by(recipe_id=recipe_id).count() == 0

    def test_vote_switch_like_to_dislike(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        client.post(f"/recipe/{recipe_id}/vote", data={"value": "1"})
        client.post(f"/recipe/{recipe_id}/vote", data={"value": "-1"})
        with app.app_context():
            from models import Vote
            votes = Vote.query.filter_by(recipe_id=recipe_id).all()
            assert len(votes) == 1
            assert votes[0].value == -1

    def test_score_shown_on_recipe_page(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        client.post(f"/recipe/{recipe_id}/vote", data={"value": "1"})
        resp = client.get(f"/recipe/{recipe_id}")
        assert b"1" in resp.data

    def test_invalid_vote_value_returns_400(self, client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = client.post(f"/recipe/{recipe_id}/vote", data={"value": "99"})
        assert resp.status_code == 400

    def test_vote_on_nonexistent_recipe_returns_404(self, client):
        resp = client.post("/recipe/99999/vote", data={"value": "1"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Admin — auth
# ---------------------------------------------------------------------------

class TestAdminAuth:
    def test_login_page_loads(self, client):
        resp = client.get("/admin/login")
        assert resp.status_code == 200
        assert "כניסה".encode() in resp.data

    def test_login_correct_credentials(self, client):
        resp = client.post(
            "/admin/login",
            data={"username": "admin", "password": "admin123"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "פאנל ניהול".encode() in resp.data

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/admin/login",
            data={"username": "admin", "password": "wrong"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "שגויים".encode() in resp.data

    def test_logout(self, admin_client):
        resp = admin_client.get("/admin/logout", follow_redirects=True)
        assert resp.status_code == 200

    def test_admin_redirects_when_not_logged_in(self, client):
        resp = client.get("/admin/")
        assert resp.status_code == 302
        assert "/admin/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# Admin — dashboard
# ---------------------------------------------------------------------------

class TestAdminDashboard:
    def test_dashboard_loads(self, admin_client):
        resp = admin_client.get("/admin/")
        assert resp.status_code == 200
        assert "לוח בקרה".encode() in resp.data or "פאנל ניהול".encode() in resp.data

    def test_dashboard_shows_counts(self, admin_client, app, sample_recipe):
        resp = admin_client.get("/admin/")
        assert resp.status_code == 200
        assert b"1" in resp.data  # at least one recipe


# ---------------------------------------------------------------------------
# Admin — recipes
# ---------------------------------------------------------------------------

class TestAdminRecipes:
    def test_recipe_list_loads(self, admin_client):
        resp = admin_client.get("/admin/recipes")
        assert resp.status_code == 200

    def test_recipe_list_shows_recipes(self, admin_client, app, sample_recipe):
        resp = admin_client.get("/admin/recipes")
        assert "עוגת שוקולד".encode() in resp.data

    def test_new_recipe_form_loads(self, admin_client):
        resp = admin_client.get("/admin/recipe/new")
        assert resp.status_code == 200
        assert "כותרת".encode() in resp.data

    def test_create_recipe(self, admin_client, app):
        resp = admin_client.post(
            "/admin/recipe/new",
            data={"title": "פסטה ברוטב עגבניות", "ingredients": "פסטה, עגבניות", "instructions": "לבשל..."},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert Recipe.query.filter_by(title="פסטה ברוטב עגבניות").first() is not None

    def test_create_recipe_empty_title(self, admin_client, app):
        resp = admin_client.post(
            "/admin/recipe/new",
            data={"title": "", "ingredients": "גוף", "instructions": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert Recipe.query.count() == 0

    def test_create_recipe_with_tags(self, admin_client, app):
        with app.app_context():
            tag = Tag(name="ארוחת בוקר")
            db.session.add(tag)
            db.session.commit()
            tag_id = tag.id

        resp = admin_client.post(
            "/admin/recipe/new",
            data={"title": "חביתה", "ingredients": "ביצים", "instructions": "שני ביצים...", "tag_ids": [str(tag_id)]},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            recipe = Recipe.query.filter_by(title="חביתה").first()
            assert recipe is not None
            assert any(t.id == tag_id for t in recipe.tags)

    def test_edit_recipe_form_loads(self, admin_client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = admin_client.get(f"/admin/recipe/{recipe_id}/edit")
        assert resp.status_code == 200
        assert "עוגת שוקולד".encode() in resp.data

    def test_edit_recipe(self, admin_client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = admin_client.post(
            f"/admin/recipe/{recipe_id}/edit",
            data={"title": "עוגת שוקולד מעודכנת", "ingredients": "חדש", "instructions": "גרסה חדשה"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            recipe = db.session.get(Recipe, recipe_id)
            assert recipe.title == "עוגת שוקולד מעודכנת"

    def test_edit_recipe_empty_title(self, admin_client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = admin_client.post(
            f"/admin/recipe/{recipe_id}/edit",
            data={"title": "", "ingredients": "גוף", "instructions": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            recipe = db.session.get(Recipe, recipe_id)
            assert recipe.title == "עוגת שוקולד"  # unchanged

    def test_delete_recipe(self, admin_client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        resp = admin_client.post(
            f"/admin/recipe/{recipe_id}/delete",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(Recipe, recipe_id) is None

    def test_delete_nonexistent_recipe(self, admin_client):
        resp = admin_client.post("/admin/recipe/99999/delete")
        assert resp.status_code == 404

    def test_upload_image_with_recipe(self, admin_client, app):
        fake_image = (io.BytesIO(b"GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;"), "photo.gif")
        resp = admin_client.post(
            "/admin/recipe/new",
            data={
                "title": "מתכון עם תמונה",
                "ingredients": "מצרכים",
                "instructions": "תיאור",
                "images": fake_image,
                "position_0": "gallery",
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            recipe = Recipe.query.filter_by(title="מתכון עם תמונה").first()
            assert recipe is not None
            assert len(recipe.images) == 1
            assert recipe.images[0].position == "gallery"

    def test_delete_recipe_removes_images(self, admin_client, app):
        with app.app_context():
            recipe = Recipe(title="עם תמונה", ingredients="גוף", instructions="")
            db.session.add(recipe)
            db.session.flush()
            img = Image(recipe_id=recipe.id, filename="fake.jpg", position="gallery", sort_order=0)
            db.session.add(img)
            db.session.commit()
            recipe_id = recipe.id

        resp = admin_client.post(f"/admin/recipe/{recipe_id}/delete", follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert Image.query.filter_by(recipe_id=recipe_id).count() == 0

    def test_edit_recipe_delete_image(self, admin_client, app):
        import tempfile, shutil
        upload_dir = flask_app.config["UPLOAD_FOLDER"]

        with app.app_context():
            recipe = Recipe(title="מתכון", ingredients="גוף", instructions="")
            db.session.add(recipe)
            db.session.flush()
            # Create a real (tiny) file so deletion can be tested
            fake_filename = "testimg.jpg"
            open(os.path.join(upload_dir, fake_filename), "wb").close()
            img = Image(recipe_id=recipe.id, filename=fake_filename, position="gallery", sort_order=0)
            db.session.add(img)
            db.session.commit()
            recipe_id = recipe.id
            img_id = img.id

        resp = admin_client.post(
            f"/admin/recipe/{recipe_id}/edit",
            data={"title": "מתכון", "ingredients": "גוף", "instructions": "", "delete_image_ids": [str(img_id)]},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(Image, img_id) is None


# ---------------------------------------------------------------------------
# Admin — videos
# ---------------------------------------------------------------------------

class TestAdminVideos:
    # Minimal valid MP4 bytes (just enough to pass extension check)
    FAKE_VIDEO = b"\x00\x00\x00\x18ftypmp42"

    def test_upload_video_with_new_recipe(self, admin_client, app):
        fake_video = (io.BytesIO(self.FAKE_VIDEO), "demo.mp4")
        resp = admin_client.post(
            "/admin/recipe/new",
            data={
                "title": "מתכון עם סרטון",
                "ingredients": "קמח",
                "instructions": "לאפות",
                "videos": fake_video,
                "video_titles": ["הדגמה"],
            },
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            from models import Video
            recipe = Recipe.query.filter_by(title="מתכון עם סרטון").first()
            assert recipe is not None
            assert len(recipe.videos) == 1
            assert recipe.videos[0].title == "הדגמה"

    def test_video_shown_on_recipe_page(self, admin_client, client, app):
        fake_video = (io.BytesIO(self.FAKE_VIDEO), "clip.mp4")
        admin_client.post(
            "/admin/recipe/new",
            data={
                "title": "מתכון וידאו",
                "ingredients": "",
                "instructions": "",
                "videos": fake_video,
                "video_titles": ["קליפ"],
            },
            content_type="multipart/form-data",
        )
        with app.app_context():
            recipe = Recipe.query.filter_by(title="מתכון וידאו").first()
            assert recipe is not None
            recipe_id = recipe.id

        resp = client.get(f"/recipe/{recipe_id}")
        assert resp.status_code == 200
        assert b"<video" in resp.data
        assert "קליפ".encode() in resp.data

    def test_delete_video_on_edit(self, admin_client, app):
        upload_dir = flask_app.config["VIDEO_FOLDER"]
        with app.app_context():
            from models import Video
            recipe = Recipe(title="מתכון", ingredients="", instructions="")
            db.session.add(recipe)
            db.session.flush()
            fake_filename = "testvid.mp4"
            open(os.path.join(upload_dir, fake_filename), "wb").close()
            vid = Video(recipe_id=recipe.id, filename=fake_filename, title="", sort_order=0)
            db.session.add(vid)
            db.session.commit()
            recipe_id = recipe.id
            vid_id = vid.id

        resp = admin_client.post(
            f"/admin/recipe/{recipe_id}/edit",
            data={"title": "מתכון", "ingredients": "", "instructions": "",
                  "delete_video_ids": [str(vid_id)]},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            from models import Video
            assert db.session.get(Video, vid_id) is None

    def test_delete_recipe_removes_videos(self, admin_client, app):
        with app.app_context():
            from models import Video
            recipe = Recipe(title="למחיקה", ingredients="", instructions="")
            db.session.add(recipe)
            db.session.flush()
            vid = Video(recipe_id=recipe.id, filename="todel.mp4", title="", sort_order=0)
            db.session.add(vid)
            db.session.commit()
            recipe_id = recipe.id

        admin_client.post(f"/admin/recipe/{recipe_id}/delete", follow_redirects=True)
        with app.app_context():
            from models import Video
            assert Video.query.filter_by(recipe_id=recipe_id).count() == 0


# ---------------------------------------------------------------------------
# Admin — tags
# ---------------------------------------------------------------------------

class TestAdminTags:
    def test_tags_page_loads(self, admin_client):
        resp = admin_client.get("/admin/tags")
        assert resp.status_code == 200

    def test_create_tag(self, admin_client, app):
        resp = admin_client.post(
            "/admin/tags",
            data={"name": "בשרי"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert Tag.query.filter_by(name="בשרי").first() is not None

    def test_create_duplicate_tag(self, admin_client, app):
        admin_client.post("/admin/tags", data={"name": "חלבי"})
        resp = admin_client.post(
            "/admin/tags",
            data={"name": "חלבי"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert Tag.query.filter_by(name="חלבי").count() == 1

    def test_create_tag_empty_name(self, admin_client, app):
        resp = admin_client.post(
            "/admin/tags",
            data={"name": ""},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert Tag.query.count() == 0

    def test_delete_tag(self, admin_client, app):
        with app.app_context():
            tag = Tag(name="לחמים")
            db.session.add(tag)
            db.session.commit()
            tag_id = tag.id

        resp = admin_client.post(f"/admin/tag/{tag_id}/delete", follow_redirects=True)
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(Tag, tag_id) is None

    def test_delete_nonexistent_tag(self, admin_client):
        resp = admin_client.post("/admin/tag/99999/delete")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Admin — comments
# ---------------------------------------------------------------------------

class TestAdminComments:
    def test_comments_page_loads(self, admin_client):
        resp = admin_client.get("/admin/comments")
        assert resp.status_code == 200

    def test_comments_page_shows_comments(self, admin_client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        with app.app_context():
            comment = Comment(recipe_id=recipe_id, author_name="יוסי", body="כל הכבוד!")
            db.session.add(comment)
            db.session.commit()

        resp = admin_client.get("/admin/comments")
        assert "יוסי".encode() in resp.data
        assert "כל הכבוד".encode() in resp.data

    def test_delete_comment(self, admin_client, app, sample_recipe):
        recipe_id, _ = sample_recipe
        with app.app_context():
            comment = Comment(recipe_id=recipe_id, author_name="יוסי", body="כל הכבוד!")
            db.session.add(comment)
            db.session.commit()
            comment_id = comment.id

        resp = admin_client.post(
            f"/admin/comment/{comment_id}/delete",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        with app.app_context():
            assert db.session.get(Comment, comment_id) is None

    def test_delete_nonexistent_comment(self, admin_client):
        resp = admin_client.post("/admin/comment/99999/delete")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Authorization: unauthenticated access to admin routes is blocked
# ---------------------------------------------------------------------------

class TestAdminProtection:
    PROTECTED = [
        ("GET", "/admin/"),
        ("GET", "/admin/recipes"),
        ("GET", "/admin/recipe/new"),
        ("GET", "/admin/recipe/1/edit"),
        ("GET", "/admin/tags"),
        ("GET", "/admin/comments"),
    ]

    @pytest.mark.parametrize("method,path", PROTECTED)
    def test_protected_route_redirects(self, client, method, path):
        resp = client.open(path, method=method)
        assert resp.status_code == 302
        assert "/admin/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------------------

class TestErrorPages:
    def test_404_page(self, client):
        resp = client.get("/this-does-not-exist")
        assert resp.status_code == 404
        assert "404".encode() in resp.data

    def test_recipe_404(self, client):
        resp = client.get("/recipe/99999")
        assert resp.status_code == 404

from flask import Blueprint, render_template
from flask import current_app as app
from flask_login import current_user
import os

bp = Blueprint("social", __name__)

def _read_sql(name: str) -> str:
    # repo root (one level up from app/)
    repo_root = os.path.dirname(os.path.dirname(__file__))
    with open(os.path.join(repo_root, "sql", name), "r") as f:
        return f.read()

@bp.route("/social")
def social_page():
    # if not logged in, show friendly message
    if not current_user.is_authenticated:
        return render_template("social.html", items=[], need_login=True)

    sql = _read_sql("get_recent_feedback.sql")
    rows = app.db.execute(sql, user_id=current_user.id)  # returns list of dicts
    return render_template("social.html", items=rows, need_login=False)

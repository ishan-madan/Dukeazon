from flask import Blueprint, render_template, current_app as app, request
from flask_login import login_required, current_user
from pathlib import Path

bp = Blueprint('social', __name__)

@bp.route('/social')
@login_required
def social_page():
    ftype = request.args.get('type', 'all').lower()
    if ftype not in ('all', 'product', 'seller'):
        ftype = 'all'

    try:
        limit = int(request.args.get('limit', 5))
    except ValueError:
        limit = 5
    limit = max(1, min(limit, 50))               

    sql_path = Path(app.root_path).parent / 'sql' / 'get_recent_feedback.sql'
    sql = sql_path.read_text()

    rows = app.db.execute(sql, user_id=current_user.id, type=ftype, limit=limit)

    return render_template('social.html', rows=rows)

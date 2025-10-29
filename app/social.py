from flask import Blueprint, render_template, current_app as app, request
from flask_login import login_required, current_user
from pathlib import Path

bp = Blueprint('social', __name__)

@bp.route('/social')
@login_required
def social_page():
    # read query params
    ftype = request.args.get('type', 'all')   # 'all' | 'product' | 'seller'
    try:
        limit = int(request.args.get('limit', 5))
    except ValueError:
        limit = 5

    sql_path = Path(app.root_path).parent / 'sql' / 'get_recent_feedback.sql'
    sql = sql_path.read_text()

    rows = app.db.execute(sql, user_id=current_user.id, limit=limit)  # list of dicts

    if ftype in ('product', 'seller'):
        rows = [r for r in rows if r['type'] == ftype]

    return render_template('social.html', rows=rows)

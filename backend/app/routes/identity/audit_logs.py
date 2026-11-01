from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from app.models import AuditLog


bp = Blueprint('audit_logs', __name__)


@bp.route('/audit-logs', methods=['GET'])
def get_audit_logs():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 25, type=int), 1), 100)
    query = AuditLog.query.options(joinedload(AuditLog.user))
    user_id = request.args.get('user_id', type=int)
    endpoint = request.args.get('endpoint', type=str)
    action = request.args.get('action', type=str)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    if endpoint:
        query = query.filter_by(endpoint=endpoint)
    if action:
        query = query.filter_by(action=action.upper())
    pagination = query.order_by(AuditLog.id.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [entry.to_dict() for entry in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })

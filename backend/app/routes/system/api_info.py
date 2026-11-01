from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from app import db


bp = Blueprint('api_info', __name__)


@bp.route('/health', methods=['GET'])
def health_check():
    try:
        db.session.execute(text('SELECT 1'))
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Health check database probe failed')
        return jsonify({'status': 'unhealthy', 'database': 'unavailable'}), 503
    return jsonify({'status': 'healthy', 'database': 'available'}), 200


@bp.route('/api-info', methods=['GET'])
def get_api_info():
    api_routes = [
        rule for rule in current_app.url_map.iter_rules()
        if rule.rule.startswith('/api/v1/')
    ]
    return jsonify({
        'name': 'DistribuFlow ERP API',
        'version': current_app.config['API_VERSION'],
        'description': current_app.config['API_DESCRIPTION'],
        'total_endpoints': len(api_routes),
        'total_modules': len({
            rule.endpoint.split('.', 1)[0]
            for rule in api_routes
        })
    })

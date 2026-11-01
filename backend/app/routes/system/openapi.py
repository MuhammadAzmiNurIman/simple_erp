from flask import Blueprint, current_app, jsonify

from app.openapi import create_openapi_spec


bp = Blueprint('openapi', __name__)


@bp.route('/openapi.json', methods=['GET'])
def openapi_spec():
    return jsonify(create_openapi_spec(current_app))

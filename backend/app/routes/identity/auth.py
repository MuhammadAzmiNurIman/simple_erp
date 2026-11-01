# app/routes/auth.py
# Auth & RBAC - Authentication & Role-Based Access Control
from flask import Blueprint, current_app, g, has_request_context, jsonify, request
from sqlalchemy import event
from sqlalchemy.orm import Session
from app import db
from app.models import AuditLog, Permission, RevokedToken, Role, User, UserWarehouseAccess
from app.authorization import (
    PERMISSION_DEFINITIONS,
    check_warehouse_scope,
    has_permission,
    required_permission,
)
from functools import wraps
import jwt
import datetime
import re
from uuid import uuid4


bp = Blueprint('auth', __name__)
TOKEN_TTL_SECONDS = 3600
REFRESH_TOKEN_TTL_SECONDS = 7 * 24 * 3600

PUBLIC_ENDPOINTS = {
    'auth.register', 'auth.login', 'auth.refresh', 'api_info.health_check',
    'openapi.openapi_spec',
}
PUBLIC_PATHS = {
    '/api/v1/health',
    '/api/v1/openapi.json',
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/auth/refresh',
}


def _audit_is_applicable():
    return (
        has_request_context()
        and getattr(g, 'audit_request_active', False)
        and request.path.startswith('/api/v1/')
        and request.method not in {'GET', 'HEAD', 'OPTIONS'}
        and getattr(request, 'current_user', None) is not None
    )


def _audit_action():
    return {
        'auth.login': 'LOGIN',
        'auth.logout': 'LOGOUT',
    }.get(request.endpoint, request.method)


def _audit_resource_id():
    if not request.view_args:
        return None
    return next((
        str(value)
        for key, value in request.view_args.items()
        if key.endswith('_id') or key == 'id'
    ), None)


@event.listens_for(Session, 'before_commit')
def add_audit_to_business_transaction(session):
    """Commit mutation audit records with the transaction they describe."""
    if not _audit_is_applicable() or getattr(g, 'audit_commit_written', False):
        return
    entry = AuditLog(
        user_id=request.current_user.id,
        action=_audit_action(),
        endpoint=request.endpoint or 'unknown',
        resource_id=_audit_resource_id(),
        status_code=200,
        ip_address=request.remote_addr,
    )
    session.add(entry)
    g.audit_commit_written = True
    g.audit_entry = entry


@event.listens_for(Session, 'after_rollback')
def reset_audit_after_rollback(session):
    if has_request_context() and getattr(g, 'audit_entry', None) is not None:
        if not getattr(g, 'audit_commit_durable', False):
            g.audit_commit_written = False
            g.audit_entry = None


@event.listens_for(Session, 'after_commit')
def mark_audit_commit_durable(session):
    if has_request_context() and getattr(g, 'audit_entry', None) is not None:
        g.audit_commit_durable = True
@bp.before_app_request
def authorize_api_request():
    """Authenticate API requests and restrict write access to operators/admins."""
    # Flask's test client can preserve request context beyond response teardown.
    # Mark only the active API request so unrelated commits in a later app
    # context cannot reuse a stale request.current_user for audit attribution.
    g.audit_request_active = request.path.startswith('/api/v1/')
    if not request.path.startswith('/api/v1/') or request.method == 'OPTIONS':
        return None

    if request.endpoint in PUBLIC_ENDPOINTS:
        return None

    if request.path in PUBLIC_PATHS and getattr(request, 'routing_exception', None) is not None:
        raise request.routing_exception

    auth_header = request.headers.get('Authorization', '')
    scheme, separator, token = auth_header.partition(' ')
    if scheme.lower() != 'bearer' or not separator or not token.strip():
        return jsonify({'error': 'Authentication required'}), 401

    try:
        payload = jwt.decode(
            token.strip(),
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        if payload.get('token_use') != 'access':
            return jsonify({'error': 'Invalid token type'}), 401
        user_id = payload.get('user_id')
        user = (
            db.session.get(User, user_id)
            if isinstance(user_id, int) and not isinstance(user_id, bool)
            else None
        )
        token_id = payload.get('jti')
        if isinstance(token_id, str) and db.session.get(RevokedToken, token_id):
            return jsonify({'error': 'Invalid or expired token'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid or expired token'}), 401

    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401

    request.current_user = user

    if getattr(request, 'routing_exception', None) is not None:
        raise request.routing_exception
    permission_code = required_permission(request.endpoint, request.method)
    if permission_code is None or not has_permission(user, permission_code):
        return jsonify({'error': 'Insufficient permissions'}), 403
    permission = db.session.get(Permission, permission_code)
    definition = PERMISSION_DEFINITIONS.get(permission_code)
    warehouse_scoped = (
        definition[3]
        if definition is not None
        else bool(permission and permission.warehouse_scoped)
    )
    if warehouse_scoped:
        scope_error = check_warehouse_scope(
            user,
            request.endpoint,
            request.view_args
        )
        if scope_error is not None:
            return scope_error

    return None


# Helper: Generate JWT token
def _encode_token(user_id, token_use, ttl_seconds):
    payload = {
        'user_id': user_id,
        'jti': str(uuid4()),
        'token_use': token_use,
        'exp': (
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(seconds=ttl_seconds)
        )
    }
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )


def generate_token(user_id):
    return _encode_token(user_id, 'access', TOKEN_TTL_SECONDS)


def generate_refresh_token(user_id):
    return _encode_token(user_id, 'refresh', REFRESH_TOKEN_TTL_SECONDS)


# Decorator: Authentication required
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Cek header Authorization
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401

        token = auth_header.split(' ')[1]
        try:
            # Decode token
            payload = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
            if not user_id:
                return jsonify({'error': 'Invalid token payload'}), 401

            # Cek user exists and active
            user = db.session.get(User, user_id)
            if not user or not user.is_active:
                return jsonify({'error': 'User not found or inactive'}), 401

            # Tambahkan user ke request context
            request.current_user = user
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)
    return decorated


# Decorator: Role-based access control
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required first'}), 401
            user = request.current_user
            if user.role not in allowed_roles:
                return jsonify({'error': f'Access denied. Required roles: {allowed_roles}, yours: {user.role}'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


@bp.route('/auth/register', methods=['POST'])
def register():
    return jsonify({
        'error': 'Public registration is disabled. Contact an administrator.'
    }), 403


@bp.route('/auth/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400

    username = data.get('username')
    password = data.get('password')

    if not isinstance(username, str) or not username or not isinstance(password, str) or not password:
        return jsonify({'error': 'Username and password required'}), 400

    # Cari user
    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401

    try:
        # Generate token
        token = generate_token(user.id)

        # Update last_login
        user.last_login = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        db.session.commit()
        request.current_user = user

        return jsonify({
            'message': 'Login successful',
            'data': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'permissions': _user_permissions(user),
                'all_warehouses': user.all_warehouses or user.role == 'admin',
                'warehouse_ids': [
                    access.warehouse_id
                    for access in UserWarehouseAccess.query.filter_by(user_id=user.id).all()
                ],
                'token': token,
                'token_type': 'Bearer',
                'expires_in': TOKEN_TTL_SECONDS,
                'refresh_token': generate_refresh_token(user.id),
                'refresh_expires_in': REFRESH_TOKEN_TTL_SECONDS
            }
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception('User login failed')
        return jsonify({'error': 'Unable to log in'}), 500


@bp.route('/auth/refresh', methods=['POST'])
def refresh():
    """Exchange a valid refresh token for a new access token."""
    data = request.get_json(silent=True)
    refresh_token = data.get('refresh_token') if isinstance(data, dict) else None
    if not refresh_token:
        scheme, _, value = request.headers.get('Authorization', '').partition(' ')
        if scheme.lower() == 'bearer' and value.strip():
            refresh_token = value.strip()
    if not isinstance(refresh_token, str) or not refresh_token:
        return jsonify({'error': 'Refresh token is required'}), 400

    try:
        payload = jwt.decode(
            refresh_token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid refresh token'}), 401

    token_id = payload.get('jti')
    user_id = payload.get('user_id')
    if (
        payload.get('token_use') != 'refresh'
        or not isinstance(token_id, str)
        or not isinstance(user_id, int)
        or isinstance(user_id, bool)
    ):
        return jsonify({'error': 'Invalid refresh token'}), 401
    if db.session.get(RevokedToken, token_id):
        return jsonify({'error': 'Refresh token has been revoked'}), 401
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({'error': 'User not found or inactive'}), 401

    expires_at = datetime.datetime.fromtimestamp(
        payload['exp'],
        tz=datetime.timezone.utc
    ).replace(tzinfo=None)
    try:
        db.session.add(RevokedToken(jti=token_id, expires_at=expires_at))
        token = generate_token(user.id)
        new_refresh_token = generate_refresh_token(user.id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Token refresh failed')
        return jsonify({'error': 'Unable to refresh token'}), 500

    request.current_user = user
    return jsonify({
        'message': 'Token refreshed successfully',
        'data': {
            'token': token,
            'token_type': 'Bearer',
            'expires_in': TOKEN_TTL_SECONDS,
            'refresh_token': new_refresh_token,
            'refresh_expires_in': REFRESH_TOKEN_TTL_SECONDS
        }
    }), 200


@bp.route('/auth/me', methods=['GET'])
@auth_required
def me():
    """Ambil profile user sedang login"""
    user = request.current_user
    return jsonify({
        'data': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'permissions': _user_permissions(user),
            'all_warehouses': user.all_warehouses or user.role == 'admin',
            'warehouse_ids': [
                access.warehouse_id
                for access in UserWarehouseAccess.query.filter_by(user_id=user.id).all()
            ],
            'is_active': user.is_active,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        }
    }), 200


@bp.route('/auth/me', methods=['PATCH'])
@auth_required
def update_my_profile():
    user = request.current_user
    data = request.get_json(silent=True)
    allowed_fields = {
        'username', 'email', 'current_password', 'new_password', 'refresh_token'
    }
    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'A non-empty JSON object is required'}), 400
    if set(data) - allowed_fields:
        return jsonify({'error': 'Unsupported profile fields were provided'}), 400
    if not any(field in data for field in ('username', 'email', 'new_password')):
        return jsonify({'error': 'No profile changes were provided'}), 400

    current_password = data.get('current_password')
    if not isinstance(current_password, str) or not user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 403

    username = data.get('username', user.username)
    email = data.get('email', user.email)
    if not isinstance(username, str) or not username.strip() or len(username.strip()) > 50:
        return jsonify({'error': 'Username must contain 1-50 characters'}), 400
    if (
        not isinstance(email, str)
        or len(email.strip()) > 100
        or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email.strip())
    ):
        return jsonify({'error': 'A valid email address is required'}), 400
    username = username.strip()
    email = email.strip()
    if User.query.filter(User.id != user.id, User.username == username).first():
        return jsonify({'error': 'Username is already in use'}), 409
    if User.query.filter(User.id != user.id, User.email == email).first():
        return jsonify({'error': 'Email is already in use'}), 409

    new_password = data.get('new_password')
    access_token_payload = None
    refresh_token_payload = None
    if 'new_password' in data:
        if not isinstance(new_password, str) or len(new_password) < 12:
            return jsonify({'error': 'New password must contain at least 12 characters'}), 400
        if user.check_password(new_password):
            return jsonify({'error': 'New password must be different from the current password'}), 400

        try:
            access_token_payload = jwt.decode(
                request.headers['Authorization'].partition(' ')[2].strip(),
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            refresh_token = data.get('refresh_token')
            if not isinstance(refresh_token, str) or not refresh_token:
                return jsonify({'error': 'Refresh token is required when changing password'}), 400
            refresh_token_payload = jwt.decode(
                refresh_token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
        except jwt.InvalidTokenError:
            return jsonify({'error': 'A valid active session is required to change password'}), 401

        refresh_jti = refresh_token_payload.get('jti')
        if (
            access_token_payload.get('token_use') != 'access'
            or refresh_token_payload.get('token_use') != 'refresh'
            or access_token_payload.get('user_id') != user.id
            or refresh_token_payload.get('user_id') != user.id
            or not isinstance(access_token_payload.get('jti'), str)
            or not isinstance(refresh_jti, str)
            or db.session.get(RevokedToken, refresh_jti)
        ):
            return jsonify({'error': 'A valid active session is required to change password'}), 401

    user.username = username
    user.email = email
    if new_password is not None:
        user.set_password(new_password)

    response_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'permissions': _user_permissions(user),
        'all_warehouses': user.all_warehouses or user.role == 'admin',
        'warehouse_ids': [
            access.warehouse_id
            for access in UserWarehouseAccess.query.filter_by(user_id=user.id).all()
        ],
    }
    if access_token_payload and refresh_token_payload:
        response_data.update({
            'token': generate_token(user.id),
            'refresh_token': generate_refresh_token(user.id),
        })
        db.session.add_all([
            RevokedToken(
                jti=access_token_payload['jti'],
                expires_at=datetime.datetime.fromtimestamp(
                    access_token_payload['exp'],
                    tz=datetime.timezone.utc
                ).replace(tzinfo=None)
            ),
            RevokedToken(
                jti=refresh_token_payload['jti'],
                expires_at=datetime.datetime.fromtimestamp(
                    refresh_token_payload['exp'],
                    tz=datetime.timezone.utc
                ).replace(tzinfo=None)
            ),
        ])

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('User profile update failed')
        return jsonify({'error': 'Unable to update profile'}), 500
    return jsonify({'data': response_data}), 200


def _user_permissions(user):
    if user.role == 'admin':
        return sorted(PERMISSION_DEFINITIONS)
    role = db.session.get(Role, user.role)
    return sorted(permission.code for permission in role.permissions) if role else []


@bp.route('/auth/logout', methods=['POST'])
def logout():
    payload = jwt.decode(
        request.headers['Authorization'].partition(' ')[2].strip(),
        current_app.config['JWT_SECRET_KEY'],
        algorithms=['HS256']
    )
    token_id = payload.get('jti')
    if not isinstance(token_id, str):
        return jsonify({'error': 'Token cannot be revoked'}), 400
    revoked_tokens = [RevokedToken(
        jti=token_id,
        expires_at=datetime.datetime.fromtimestamp(
            payload['exp'],
            tz=datetime.timezone.utc
        ).replace(tzinfo=None)
    )]

    data = request.get_json(silent=True)
    refresh_token = data.get('refresh_token') if isinstance(data, dict) else None
    if isinstance(refresh_token, str) and refresh_token:
        try:
            refresh_payload = jwt.decode(
                refresh_token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
        except jwt.InvalidTokenError:
            refresh_payload = None
        if (
            refresh_payload
            and refresh_payload.get('token_use') == 'refresh'
            and isinstance(refresh_payload.get('jti'), str)
            and not db.session.get(RevokedToken, refresh_payload['jti'])
        ):
            revoked_tokens.append(RevokedToken(
                jti=refresh_payload['jti'],
                expires_at=datetime.datetime.fromtimestamp(
                    refresh_payload['exp'],
                    tz=datetime.timezone.utc
                ).replace(tzinfo=None)
            ))

    try:
        db.session.add_all(revoked_tokens)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('User logout failed')
        return jsonify({'error': 'Unable to log out'}), 500
    return jsonify({'message': 'Logout successful'}), 200


@bp.after_app_request
def record_audit_event(response):
    if _audit_is_applicable():
        try:
            entry = getattr(g, 'audit_entry', None)
            if entry is not None and entry.id is not None:
                # The business change and audit row already committed together;
                # finalize the HTTP result code in a small follow-up update.
                db.session.query(AuditLog).filter_by(id=entry.id).update(
                    {'status_code': response.status_code},
                    synchronize_session=False
                )
            else:
                # Validation failures and rejected requests have no business
                # commit to join, but remain visible in the audit trail.
                entry = AuditLog(
                    user_id=request.current_user.id,
                    action=_audit_action(),
                    endpoint=request.endpoint or 'unknown',
                    resource_id=_audit_resource_id(),
                    status_code=response.status_code,
                    ip_address=request.remote_addr,
                )
                db.session.add(entry)
                g.audit_commit_written = True
                g.audit_entry = entry
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.critical(
                'Audit event persistence failed: user_id=%s method=%s endpoint=%s status=%s ip=%s',
                request.current_user.id,
                request.method,
                request.endpoint or 'unknown',
                response.status_code,
                request.remote_addr,
                exc_info=True
            )
    if has_request_context():
        g.audit_request_active = False
    return response

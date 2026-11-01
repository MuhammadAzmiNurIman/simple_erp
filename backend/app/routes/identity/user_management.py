import re
import secrets

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_

from app import db
from app.models import (
    Permission, Role, RoleDefaultPermission, RolePermissionOverride, User,
    UserWarehouseAccess, Warehouse,
)
from app.authorization import PERMISSION_DEFINITIONS, ROLE_DEFAULTS


bp = Blueprint('user_management', __name__)


def _set_warehouse_access(user, warehouse_ids, all_warehouses):
    if not isinstance(all_warehouses, bool):
        return jsonify({'error': 'all_warehouses must be a boolean'}), 400
    if not isinstance(warehouse_ids, list):
        return jsonify({'error': 'warehouse_ids must be a list'}), 400
    if any(not isinstance(value, int) or isinstance(value, bool) for value in warehouse_ids):
        return jsonify({'error': 'warehouse_ids must contain integer IDs'}), 400
    if len(warehouse_ids) != len(set(warehouse_ids)):
        return jsonify({'error': 'warehouse_ids must not contain duplicates'}), 400
    if user.role == 'admin':
        if warehouse_ids:
            return jsonify({'error': 'Admin users must have access to all warehouses'}), 400
        all_warehouses = True
    elif all_warehouses:
        return jsonify({'error': 'Only Admin users may access all warehouses'}), 400
    if all_warehouses and warehouse_ids:
        return jsonify({
            'error': 'Specify either all_warehouses or warehouse_ids, not both'
        }), 400

    warehouses = Warehouse.query.filter(
        Warehouse.id.in_(warehouse_ids),
        Warehouse.is_active.is_(True)
    ).all()
    if len(warehouses) != len(set(warehouse_ids)):
        return jsonify({'error': 'One or more warehouses were not found'}), 404
    if user.role != 'admin' and not warehouses:
        available_warehouses = Warehouse.query.filter_by(is_active=True).order_by(Warehouse.id).all()
        if not available_warehouses:
            return jsonify({'error': 'No active warehouse is available for this user'}), 409
        warehouses = [secrets.choice(available_warehouses)]
    user.all_warehouses = all_warehouses
    user.warehouse_access = [
        UserWarehouseAccess(warehouse_id=warehouse.id)
        for warehouse in warehouses
    ]
    return None


def _user_dict(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'is_active': user.is_active,
        'all_warehouses': user.all_warehouses or user.role == 'admin',
        'warehouse_ids': sorted(access.warehouse_id for access in user.warehouse_access),
        'last_login': user.last_login.isoformat() if user.last_login else None,
        'created_at': user.created_at.isoformat() if user.created_at else None,
    }


@bp.route('/permissions', methods=['GET'])
def get_permissions():
    module = request.args.get('module', type=str)
    # The code-defined catalog is authoritative. Historical permission rows
    # outside it are reported by the reconciliation CLI but cannot be granted
    # through the UI as if they were active system capabilities.
    query = Permission.query.filter(Permission.code.in_(PERMISSION_DEFINITIONS))
    if module:
        query = query.filter_by(module=module)
    permissions = query.order_by(
        Permission.module, Permission.action, Permission.code
    ).all()
    return jsonify({
        'data': [
            {
                'code': permission.code,
                'name': permission.name,
                'module': permission.module,
                'action': permission.action,
                'warehouse_scoped': PERMISSION_DEFINITIONS.get(
                    permission.code,
                    (None, None, None, permission.warehouse_scoped),
                )[3],
            }
            for permission in permissions
        ]
    })


@bp.route('/users', methods=['GET'])
def get_users():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 1), 100)
    query = User.query
    role = request.args.get('role', type=str)
    active = request.args.get('active', type=str)
    search = request.args.get('search', type=str)
    if role:
        query = query.filter_by(role=role)
    if active in {'true', 'false'}:
        query = query.filter_by(is_active=active == 'true')
    if search:
        query = query.filter(
            or_(User.username.ilike(f'%{search}%'), User.email.ilike(f'%{search}%'))
        )
    pagination = query.order_by(User.id).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    return jsonify({
        'data': [_user_dict(user) for user in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages,
    })


@bp.route('/users', methods=['POST'])
def create_managed_user():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role_code = data.get('role')
    if not isinstance(username, str) or not username.strip() or len(username) > 50:
        return jsonify({'error': 'A valid username is required'}), 400
    if not isinstance(email, str) or not email.strip() or len(email) > 100:
        return jsonify({'error': 'A valid email is required'}), 400
    if not isinstance(password, str) or len(password) < 12:
        return jsonify({'error': 'Password must contain at least 12 characters'}), 400
    role = db.session.get(Role, role_code) if isinstance(role_code, str) else None
    if not role:
        return jsonify({'error': 'A valid role is required'}), 400
    if User.query.filter(
        or_(User.username == username.strip(), User.email == email.strip())
    ).first():
        return jsonify({'error': 'Username or email already exists'}), 409

    user = User(
        username=username.strip(),
        email=email.strip(),
        role=role.code
    )
    user.set_password(password)
    scope_error = _set_warehouse_access(
        user,
        data.get('warehouse_ids', []),
        data.get('all_warehouses', False)
    )
    if scope_error:
        return scope_error
    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Managed user creation failed')
        return jsonify({'error': 'Unable to create user'}), 500
    return jsonify({'data': _user_dict(user)}), 201


@bp.route('/users/<int:user_id>', methods=['PATCH'])
def update_managed_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json()
    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'A non-empty JSON object is required'}), 400
    previous_role = user.role
    if 'role' in data:
        role = db.session.get(Role, data['role']) if isinstance(data['role'], str) else None
        if not role:
            return jsonify({'error': 'A valid role is required'}), 400
        user.role = role.code
    if 'is_active' in data:
        if not isinstance(data['is_active'], bool):
            return jsonify({'error': 'is_active must be a boolean'}), 400
        user.is_active = data['is_active']
    if 'password' in data:
        password = data['password']
        if not isinstance(password, str) or len(password) < 12:
            return jsonify({'error': 'Password must contain at least 12 characters'}), 400
        user.set_password(password)
    if user.role == 'admin':
        scope_error = _set_warehouse_access(user, [], True)
        if scope_error:
            return scope_error
    elif 'warehouse_ids' in data or 'all_warehouses' in data:
        scope_error = _set_warehouse_access(
            user,
            data.get(
                'warehouse_ids',
                [access.warehouse_id for access in user.warehouse_access]
            ),
            data.get(
                'all_warehouses',
                user.all_warehouses if previous_role != 'admin' else False
            )
        )
        if scope_error:
            return scope_error
    elif previous_role == 'admin' or user.all_warehouses:
        scope_error = _set_warehouse_access(user, [], False)
        if scope_error:
            return scope_error
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Managed user update failed')
        return jsonify({'error': 'Unable to update user'}), 500
    return jsonify({'data': _user_dict(user)})


@bp.route('/roles', methods=['GET'])
def get_roles():
    return jsonify({'data': [role.to_dict() for role in Role.query.order_by(Role.code).all()]})


@bp.route('/roles', methods=['POST'])
def create_role():
    data = request.get_json()
    if not isinstance(data, dict):
        return jsonify({'error': 'A JSON object is required'}), 400
    name = data.get('name')
    code = data.get('code')
    if not isinstance(name, str) or not name.strip() or len(name) > 80:
        return jsonify({'error': 'A valid role name is required'}), 400
    if not isinstance(code, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{1,19}', code):
        return jsonify({'error': 'Role code must be 2-20 lowercase characters'}), 400
    description = data.get('description')
    if description is not None and (
        not isinstance(description, str) or len(description) > 255
    ):
        return jsonify({'error': 'description must be at most 255 characters'}), 400
    if db.session.get(Role, code) or Role.query.filter_by(name=name.strip()).first():
        return jsonify({'error': 'Role code or name already exists'}), 409
    role = Role(
        code=code,
        name=name.strip(),
        description=description,
        permissions=[db.session.get(Permission, 'profile.read')],
    )
    try:
        db.session.add(role)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Role creation failed')
        return jsonify({'error': 'Unable to create role'}), 500
    return jsonify({'data': role.to_dict()}), 201


@bp.route('/roles/<string:role_code>/permissions', methods=['PUT'])
def replace_role_permissions(role_code):
    role = db.session.get(Role, role_code)
    if not role:
        return jsonify({'error': 'Role not found'}), 404
    data = request.get_json()
    permission_codes = data.get('permissions') if isinstance(data, dict) else None
    if not isinstance(permission_codes, list) or any(
        not isinstance(code, str) for code in permission_codes
    ):
        return jsonify({'error': 'permissions must be a list of permission codes'}), 400
    requested = set(permission_codes)
    requested.add('profile.read')
    unknown_codes = requested - set(PERMISSION_DEFINITIONS)
    if unknown_codes:
        return jsonify({
            'error': 'One or more permissions are not part of the active permission catalog',
            'unknown_permissions': sorted(unknown_codes),
        }), 400
    if role.code == 'admin':
        requested = set(PERMISSION_DEFINITIONS)
    permissions = Permission.query.filter(Permission.code.in_(requested)).all()
    if len(permissions) != len(requested):
        return jsonify({'error': 'One or more permissions are not defined'}), 400
    if role.is_system and role.code != 'admin':
        default_codes = set(ROLE_DEFAULTS.get(role.code, set()))
        previous_defaults = {
            row.permission_code
            for row in RoleDefaultPermission.query.filter_by(role_code=role.code).all()
        }
        if not previous_defaults:
            # Capture the current code profile as the baseline before storing
            # intentional deviations made through this endpoint.
            db.session.add_all([
                RoleDefaultPermission(role_code=role.code, permission_code=code)
                for code in sorted(default_codes)
            ])
        current_overrides = {
            row.permission_code: row
            for row in RolePermissionOverride.query.filter_by(role_code=role.code).all()
        }
        affected_codes = default_codes | requested | set(current_overrides)
        for code in affected_codes:
            requested_grant = code in requested
            default_grant = code in default_codes
            override = current_overrides.get(code)
            if requested_grant == default_grant:
                if override is not None:
                    db.session.delete(override)
            elif override is None:
                db.session.add(RolePermissionOverride(
                    role_code=role.code,
                    permission_code=code,
                    is_granted=requested_grant
                ))
            else:
                override.is_granted = requested_grant
    role.permissions = permissions
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Role permission update failed')
        return jsonify({'error': 'Unable to update role permissions'}), 500
    return jsonify({'data': role.to_dict()})

import os
import sys
import secrets
import click
from pathlib import Path
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_smorest import Api
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.http import HTTP_STATUS_CODES

# Add the backend directory to path so we can import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

db = SQLAlchemy()
ma = Marshmallow()
migrate = Migrate()

def create_app(config_class=Config):
    """Application factory that creates a Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize smorest API (reads title/version/description from app.config)
    api = Api(app)

    db.init_app(app)
    ma.init_app(app)
    migrate.init_app(app, db)

    # Initialize CORS for frontend integration
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})

    # Initialize rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=app.config['RATELIMIT_STORAGE_URI'],
        default_limits=app.config['RATELIMIT_DEFAULT_LIMITS']
    )

    # Register blueprints dari folder routes/modular
    from app.routes import register_blueprints
    register_blueprints(app)

    # Standardized application-wide error handlers
    from flask import jsonify
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Standardized JSON format for all HTTP errors."""
        payload = {
            'error': e.description or e.name,
            'code': e.code,
            'status': e.name,
        }
        data = getattr(e, 'data', None)
        if data and isinstance(data, dict):
            if 'message' in data and data['message']:
                payload['error'] = data['message']
                payload['message'] = data['message']
            if 'messages' in data:
                payload['errors'] = data['messages']
            elif 'errors' in data:
                payload['errors'] = data['errors']

        response = jsonify(payload)
        response.status_code = e.code
        return response

    @app.errorhandler(Exception)
    def handle_unhandled_exception(e):
        """Sanitized JSON format for unhandled server exceptions."""
        if isinstance(e, HTTPException):
            return handle_http_exception(e)
        db.session.rollback()
        app.logger.exception('Unhandled exception occurred: %s', e)
        return jsonify({
            'error': 'Internal server error',
            'code': 500,
            'status': 'Internal Server Error'
        }), 500

    @app.after_request
    def normalize_error_response(response):
        """Ensure every JSON error response uses {error, code, status}."""
        if response.status_code < 400 or not response.is_json:
            return response
        payload = response.get_json(silent=True)
        if not isinstance(payload, dict) or 'error' not in payload:
            return response
        payload.setdefault('code', response.status_code)
        payload.setdefault(
            'status',
            HTTP_STATUS_CODES.get(response.status_code, 'Error')
        )
        response.set_data(app.json.dumps(payload))
        response.content_type = 'application/json'
        return response

    def create_account(username, email, password, role, all_warehouses=False):
        from app.models import Role, User, UserWarehouseAccess, Warehouse

        username = username.strip()
        email = email.strip()
        if (
            not username or len(username) > 50
            or not email or len(email) > 100
            or not password
        ):
            raise click.ClickException('Invalid username, email, or password.')
        if User.query.filter(
            (User.username == username) | (User.email == email)
        ).first():
            raise click.ClickException('Username or email is already registered.')
        if db.session.get(Role, role) is None:
            raise click.ClickException(
                'Unknown role. Run "flask seed-authorization" before creating users.'
            )

        if role == 'admin':
            all_warehouses = True
        else:
            all_warehouses = False
            available_warehouses = Warehouse.query.filter_by(is_active=True).all()
            if not available_warehouses:
                raise click.ClickException(
                    'Create an active warehouse before creating non-Admin users.'
                )

        user = User(
            username=username,
            email=email,
            role=role,
            all_warehouses=all_warehouses
        )
        user.set_password(password)
        if role != 'admin':
            warehouse = secrets.choice(available_warehouses)
            user.warehouse_access = [
                UserWarehouseAccess(warehouse_id=warehouse.id)
            ]
        db.session.add(user)
        db.session.commit()
        click.echo(f'{role.capitalize()} account {username} created.')

    @app.cli.command('seed-authorization')
    def seed_authorization_command():
        """Create built-in roles and permissions without overwriting custom changes."""
        from app.authorization import seed_authorization

        seed_authorization()
        click.echo('Built-in roles and permissions are available.')

    @app.cli.command('sync-role-permissions')
    @click.option('--yes', is_flag=True, help='Confirm syncing built-in role defaults while retaining recorded overrides.')
    def sync_role_permissions_command(yes):
        """Sync built-in role defaults without discarding intentional overrides."""
        if not yes:
            click.confirm(
                'Apply updated built-in role defaults and preserve recorded custom grants and denials?',
                abort=True
            )
        from app.authorization import sync_system_role_permissions

        sync_system_role_permissions()
        click.echo('Built-in role permissions synchronized; recorded custom grants and denials were preserved.')

    @app.cli.command('reconcile-role-permissions')
    @click.option(
        '--apply', 'apply_changes', is_flag=True,
        help='Apply the reviewed plan. Without this flag, the command only reports changes.'
    )
    @click.option(
        '--snapshot-file', type=click.Path(path_type=Path, dir_okay=False),
        help='Path for the required pre-change JSON snapshot (defaults to backend/db_backups).'
    )
    def reconcile_role_permissions_command(apply_changes, snapshot_file):
        """Report or reconcile built-in role grants against the code matrix."""
        import json
        from datetime import datetime, timezone
        from flask import current_app
        from app.authorization import (
            apply_system_role_permission_reconciliation,
            plan_system_role_permission_reconciliation,
        )
        from app.models import Role, RoleDefaultPermission, RolePermissionOverride

        report = plan_system_role_permission_reconciliation()
        if not apply_changes:
            click.echo(json.dumps(report, indent=2, ensure_ascii=False))
            click.echo(
                '\nDry run only. Review untracked/unknown grants, then rerun with --apply to reconcile.'
            )
            return

        if not click.confirm(
            'Apply this plan? Untracked and unknown grants will be removed; '
            'recorded overrides will be retained.',
            default=False,
        ):
            raise click.Abort()

        if snapshot_file is None:
            backup_dir = Path(current_app.root_path).parent / 'db_backups'
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            snapshot_file = backup_dir / f'role-permissions-before-reconcile-{stamp}.json'
        else:
            snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        if snapshot_file.exists():
            raise click.ClickException(f'Snapshot file already exists: {snapshot_file}')

        snapshot = {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'role_permissions': {
                role.code: sorted(permission.code for permission in role.permissions)
                for role in Role.query.order_by(Role.code).all()
            },
            'role_permission_overrides': [
                {
                    'role_code': row.role_code,
                    'permission_code': row.permission_code,
                    'is_granted': row.is_granted,
                }
                for row in RolePermissionOverride.query.order_by(
                    RolePermissionOverride.role_code,
                    RolePermissionOverride.permission_code,
                ).all()
            ],
            'role_default_permissions': [
                {
                    'role_code': row.role_code,
                    'permission_code': row.permission_code,
                }
                for row in RoleDefaultPermission.query.order_by(
                    RoleDefaultPermission.role_code,
                    RoleDefaultPermission.permission_code,
                ).all()
            ],
            'plan': report,
        }
        snapshot_file.write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        try:
            applied_report = apply_system_role_permission_reconciliation()
        except Exception as error:
            raise click.ClickException(
                f'Reconciliation failed; database transaction rolled back. '
                f'Snapshot retained at {snapshot_file}. {error}'
            ) from error
        click.echo(json.dumps(applied_report, indent=2, ensure_ascii=False))
        click.echo(f'Role permissions reconciled. Snapshot saved to {snapshot_file}.')

    @app.cli.command('create-admin')
    def create_admin():
        """Create an administrator account from the command line."""
        username = click.prompt('Admin username')
        email = click.prompt('Admin email')
        password = click.prompt(
            'Admin password',
            hide_input=True,
            confirmation_prompt=True
        )
        create_account(username, email, password, 'admin', all_warehouses=True)

    @app.cli.command('create-user')
    @click.option(
        '--role',
        type=click.Choice([
            'operator', 'viewer', 'purchasing', 'warehouse',
            'sales', 'finance', 'manager'
        ]),
        default='operator',
        show_default=True
    )
    def create_user(role):
        """Create an operator or viewer account from the command line."""
        username = click.prompt('Username')
        email = click.prompt('Email')
        password = click.prompt(
            'Password',
            hide_input=True,
            confirmation_prompt=True
        )
        create_account(username, email, password, role)

    return app

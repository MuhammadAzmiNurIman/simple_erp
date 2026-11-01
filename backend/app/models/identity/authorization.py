from app import db


role_permissions = db.Table(
    'role_permissions',
    db.Column('role_code', db.String(32), db.ForeignKey('roles.code'), primary_key=True),
    db.Column(
        'permission_code',
        db.String(64),
        db.ForeignKey('permissions.code'),
        primary_key=True
    )
)


class RolePermissionOverride(db.Model):
    __tablename__ = 'role_permission_overrides'

    role_code = db.Column(db.String(32), db.ForeignKey('roles.code'), primary_key=True)
    permission_code = db.Column(db.String(64), db.ForeignKey('permissions.code'), primary_key=True)
    is_granted = db.Column(db.Boolean, nullable=False)


class RoleDefaultPermission(db.Model):
    __tablename__ = 'role_default_permissions'

    role_code = db.Column(db.String(32), db.ForeignKey('roles.code'), primary_key=True)
    permission_code = db.Column(db.String(64), db.ForeignKey('permissions.code'), primary_key=True)


class Role(db.Model):
    __tablename__ = 'roles'

    code = db.Column(db.String(32), primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.String(255))
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    permissions = db.relationship(
        'Permission',
        secondary=role_permissions,
        back_populates='roles'
    )

    def to_dict(self):
        return {
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'is_system': self.is_system,
            'permissions': sorted(permission.code for permission in self.permissions),
        }


class Permission(db.Model):
    __tablename__ = 'permissions'

    code = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(40), nullable=False)
    action = db.Column(db.String(30), nullable=False)
    warehouse_scoped = db.Column(db.Boolean, nullable=False, default=False)
    roles = db.relationship(
        'Role',
        secondary=role_permissions,
        back_populates='permissions'
    )


class UserWarehouseAccess(db.Model):
    __tablename__ = 'user_warehouse_access'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'warehouse_id', name='uq_user_warehouse_access'),
    )

    user = db.relationship('User', back_populates='warehouse_access')
    warehouse = db.relationship('Warehouse')


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(10), nullable=False)
    endpoint = db.Column(db.String(120), nullable=False)
    resource_id = db.Column(db.String(80))
    status_code = db.Column(db.Integer, nullable=False)
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    user = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'action': self.action,
            'endpoint': self.endpoint,
            'resource_id': self.resource_id,
            'status_code': self.status_code,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class RevokedToken(db.Model):
    __tablename__ = 'revoked_tokens'

    jti = db.Column(db.String(36), primary_key=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

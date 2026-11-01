from app import db


class InventoryQuarantine(db.Model):
    __tablename__ = 'inventory_quarantines'
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='ck_inventory_quarantines_quantity'),
        db.CheckConstraint(
            "status IN ('QUARANTINED', 'RELEASED', 'SCRAPPED')",
            name='ck_inventory_quarantines_status',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    source_sales_return_item_id = db.Column(
        db.Integer,
        db.ForeignKey('sales_return_items.id'),
        nullable=False,
        unique=True,
    )
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=False)
    quantity = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)
    unit_cost = db.Column(db.Numeric(15, 4), nullable=False, default=0)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='QUARANTINED')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    resolved_at = db.Column(db.DateTime)

    source_sales_return_item = db.relationship('SalesReturnItem')
    product = db.relationship('Product')
    warehouse = db.relationship('Warehouse')
    creator = db.relationship('User', foreign_keys=[created_by])
    actions = db.relationship(
        'InventoryQuarantineAction',
        back_populates='quarantine',
        cascade='all, delete-orphan',
        order_by='InventoryQuarantineAction.id',
    )

    @property
    def sales_return(self):
        return self.source_sales_return_item.sales_return

    def to_dict(self):
        sales_return = self.sales_return
        return {
            'id': self.id,
            'source_sales_return_item_id': self.source_sales_return_item_id,
            'sales_return_id': sales_return.id,
            'return_number': sales_return.return_number,
            'product_id': self.product_id,
            'product_name': self.product.name,
            'warehouse_id': self.warehouse_id,
            'warehouse_code': self.warehouse.code,
            'quantity': self.quantity,
            'unit_cost': float(self.unit_cost or 0),
            'reason': self.reason,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'actions': [action.to_dict() for action in self.actions],
        }


class InventoryQuarantineAction(db.Model):
    __tablename__ = 'inventory_quarantine_actions'
    __table_args__ = (
        db.CheckConstraint(
            "action IN ('RELEASE', 'SCRAP')",
            name='ck_inventory_quarantine_actions_action',
        ),
        db.CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED', 'POSTED')",
            name='ck_inventory_quarantine_actions_status',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    quarantine_id = db.Column(
        db.Integer,
        db.ForeignKey('inventory_quarantines.id'),
        nullable=False,
        index=True,
    )
    action = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='PENDING')
    reason = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    posted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    quarantine = db.relationship('InventoryQuarantine', back_populates='actions')
    creator = db.relationship('User', foreign_keys=[created_by])
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    poster = db.relationship('User', foreign_keys=[posted_by])

    def to_dict(self):
        return {
            'id': self.id,
            'quarantine_id': self.quarantine_id,
            'action': self.action,
            'status': self.status,
            'reason': self.reason,
            'created_by': self.created_by,
            'created_by_username': self.creator.username if self.creator else None,
            'reviewed_by': self.reviewed_by,
            'reviewed_by_username': self.reviewer.username if self.reviewer else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'posted_by': self.posted_by,
            'posted_by_username': self.poster.username if self.poster else None,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

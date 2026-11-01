from app import db


class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'

    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(40), nullable=False, unique=True)
    source_warehouse_id = db.Column(
        db.Integer,
        db.ForeignKey('warehouses.id'),
        nullable=False
    )
    destination_warehouse_id = db.Column(
        db.Integer,
        db.ForeignKey('warehouses.id'),
        nullable=False
    )
    status = db.Column(db.String(20), nullable=False, default='DRAFT')
    reason = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    submitted_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    rejected_at = db.Column(db.DateTime)
    posted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    source_warehouse = db.relationship(
        'Warehouse',
        foreign_keys=[source_warehouse_id]
    )
    destination_warehouse = db.relationship(
        'Warehouse',
        foreign_keys=[destination_warehouse_id]
    )
    items = db.relationship(
        'StockTransferItem',
        back_populates='transfer',
        cascade='all, delete-orphan'
    )
    creator = db.relationship('User', foreign_keys=[created_by])
    approver = db.relationship('User', foreign_keys=[approved_by])
    rejector = db.relationship('User', foreign_keys=[rejected_by])
    poster = db.relationship('User', foreign_keys=[posted_by])

    def to_dict(self):
        return {
            'id': self.id,
            'transfer_number': self.transfer_number,
            'source_warehouse_id': self.source_warehouse_id,
            'destination_warehouse_id': self.destination_warehouse_id,
            'status': self.status,
            'reason': self.reason,
            'created_by': self.created_by,
            'approved_by': self.approved_by,
            'approved_by_username': self.approver.username if self.approver else None,
            'posted_by': self.posted_by,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejected_by': self.rejected_by,
            'rejected_by_username': self.rejector.username if self.rejector else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'items': [item.to_dict() for item in self.items],
        }


class StockTransferItem(db.Model):
    __tablename__ = 'stock_transfer_items'

    id = db.Column(db.Integer, primary_key=True)
    stock_transfer_id = db.Column(
        db.Integer,
        db.ForeignKey('stock_transfers.id'),
        nullable=False
    )
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Numeric(15, 4, asdecimal=False), nullable=False)

    transfer = db.relationship('StockTransfer', back_populates='items')
    product = db.relationship('Product')

    def to_dict(self):
        return {
            'id': self.id,
            'product_id': self.product_id,
            'quantity': self.quantity,
        }

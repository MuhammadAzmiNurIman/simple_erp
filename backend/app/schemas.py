from . import ma
from .models import Product, Category, Unit, Warehouse, InventoryBalance, StockMovement


class CategorySchema(ma.Schema):
    id = ma.Integer(dump_only=True)
    name = ma.String(required=True)
    description = ma.String()
    is_active = ma.Boolean()
    created_at = ma.DateTime(dump_only=True)
    updated_at = ma.DateTime(dump_only=True)

    class Meta:
        fields = ('id', 'name', 'description', 'is_active', 'created_at', 'updated_at')


class UnitSchema(ma.Schema):
    id = ma.Integer(dump_only=True)
    name = ma.String(required=True)
    symbol = ma.String()
    is_active = ma.Boolean()
    created_at = ma.DateTime(dump_only=True)
    updated_at = ma.DateTime(dump_only=True)

    class Meta:
        fields = ('id', 'name', 'symbol', 'is_active', 'created_at', 'updated_at')


class ProductSchema(ma.Schema):
    id = ma.Integer(dump_only=True)
    sku = ma.String(required=True)
    name = ma.String(required=True)
    category_id = ma.Integer()
    unit_id = ma.Integer()
    sales_price = ma.Float(allow_none=True)
    min_stock = ma.Float()
    is_active = ma.Boolean()
    created_at = ma.DateTime(dump_only=True)
    updated_at = ma.DateTime(dump_only=True)

    category = ma.Nested(CategorySchema, dump_only=True)
    unit = ma.Nested(UnitSchema, dump_only=True)

    class Meta:
        fields = (
            'id', 'sku', 'name', 'category_id', 'unit_id', 'sales_price',
            'min_stock', 'is_active', 'created_at', 'updated_at',
            'category', 'unit'
        )


class WarehouseSchema(ma.Schema):
    id = ma.Integer(dump_only=True)
    code = ma.String(required=True)
    name = ma.String(required=True)
    address = ma.String()
    is_active = ma.Boolean()
    created_at = ma.DateTime(dump_only=True)
    updated_at = ma.DateTime(dump_only=True)

    class Meta:
        fields = ('id', 'code', 'name', 'address', 'is_active', 'created_at', 'updated_at')


class InventoryBalanceSchema(ma.Schema):
    id = ma.Integer(dump_only=True)
    product_id = ma.Integer()
    warehouse_id = ma.Integer()
    quantity_on_hand = ma.Float()
    quantity_reserved = ma.Float()
    quantity_available = ma.Float(dump_only=True)
    average_cost = ma.Float()
    last_cost = ma.Float()
    total_value = ma.Float(dump_only=True)
    updated_at = ma.DateTime(dump_only=True)

    class Meta:
        fields = ('id', 'product_id', 'warehouse_id', 'quantity_on_hand', 
                  'quantity_reserved', 'quantity_available', 'average_cost', 
                  'last_cost', 'total_value', 'updated_at')


class StockMovementSchema(ma.Schema):
    id = ma.Integer(dump_only=True)
    product_id = ma.Integer()
    warehouse_id = ma.Integer()
    movement_type = ma.String(required=True)
    quantity_delta = ma.Float(required=True)
    unit_cost = ma.Float(required=True)
    reference_type = ma.String()
    reference_id = ma.Integer()
    created_by = ma.Integer()
    is_inbound = ma.Boolean(dump_only=True)
    is_outbound = ma.Boolean(dump_only=True)
    created_at = ma.DateTime(dump_only=True)

    class Meta:
        fields = ('id', 'product_id', 'warehouse_id', 'movement_type', 
                  'quantity_delta', 'unit_cost', 'reference_type', 
                  'reference_id', 'created_by', 'is_inbound', 
                  'is_outbound', 'created_at')


# Singleton schemas
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
unit_schema = UnitSchema()
units_schema = UnitSchema(many=True)
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)
warehouse_schema = WarehouseSchema()
warehouses_schema = WarehouseSchema(many=True)
inventory_balance_schema = InventoryBalanceSchema()
inventory_balances_schema = InventoryBalanceSchema(many=True)
stock_movement_schema = StockMovementSchema()
stock_movements_schema = StockMovementSchema(many=True)

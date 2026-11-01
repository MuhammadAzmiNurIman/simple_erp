import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context
import sqlalchemy as sa

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db
LEGACY_TABLES = {
    'categories', 'customers', 'suppliers', 'units', 'users', 'warehouses',
    'products', 'purchase_orders', 'sales_orders', 'supplier_payments',
    'goods_receipts', 'inventory_balances', 'purchase_order_items',
    'sales_order_items', 'shipments', 'stock_movements', 'goods_receipt_items',
    'inventory_adjusters', 'invoices', 'shipment_items', 'vendor_bills',
    'payments', 'supplier_payment_allocations',
    'customer_payment_allocations',
}
LEGACY_TRANSACTION_TABLES = LEGACY_TABLES - {
    'categories', 'customers', 'suppliers', 'units', 'users', 'warehouses',
    'products',
}

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def validate_legacy_database(connection):
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    if not tables:
        return
    has_unapplied_version_table = False
    if 'alembic_version' in tables:
        has_revision = connection.execute(
            sa.text('SELECT 1 FROM alembic_version LIMIT 1')
        ).scalar_one_or_none()
        if has_revision is not None:
            return
        has_unapplied_version_table = True
        tables.remove('alembic_version')

    def abort(message):
        if has_unapplied_version_table:
            connection.execute(sa.text('DROP TABLE alembic_version'))
            connection.commit()
        raise RuntimeError(message)

    unexpected_tables = tables - LEGACY_TABLES
    if unexpected_tables:
        abort(
            'Legacy database contains unrecognized tables; migration stopped '
            f'without changes: {", ".join(sorted(unexpected_tables))}.'
        )
    if connection.dialect.name != 'sqlite':
        abort(
            'Automatic legacy adoption is currently supported only for the '
            'known SQLite schema. No schema changes were applied.'
        )

    populated = []
    for table in sorted(tables & LEGACY_TRANSACTION_TABLES):
        count = connection.execute(
            sa.text(f'SELECT COUNT(*) FROM "{table}"')
        ).scalar_one()
        if count:
            populated.append(f'{table}={count}')
    if populated:
        abort(
            'Legacy adoption stopped before schema changes because business '
            'transactions need an explicit data mapping: '
            f'{", ".join(populated)}. Back up the database and map these '
            'records before retrying.'
        )


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=get_metadata(), literal_binds=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        validate_legacy_database(connection)
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            transaction_per_migration=True,
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

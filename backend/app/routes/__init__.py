"""Route registration organized around business domains."""

from .identity import audit_logs, auth, user_management
from . import finance
from .inventory import adjustments, balances, movements, quarantine, transfers
from .master_data import categories, partners, product, units, warehouse
from .purchasing import transactions as purchasing
from .reporting import reports, statistics
from .sales import returns as sales_returns, transactions as sales
from .system import api_info, openapi


def register_blueprints(app):
    """Register all API blueprints without changing their public URL rules."""
    blueprints = (
        product.bp,
        warehouse.bp,
        balances.bp,
        categories.bp,
        units.bp,
        movements.bp,
        purchasing.bp,
        finance.bp,
        sales.bp,
        sales_returns.bp,
        adjustments.bp,
        reports.bp,
        statistics.bp,
        auth.bp,
        partners.customers_bp,
        partners.suppliers_bp,
        api_info.bp,
        openapi.bp,
        audit_logs.bp,
        user_management.bp,
        transfers.bp,
        quarantine.bp,
    )
    for blueprint in blueprints:
        app.register_blueprint(blueprint, url_prefix='/api/v1')

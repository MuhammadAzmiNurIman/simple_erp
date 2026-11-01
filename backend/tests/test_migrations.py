from sqlalchemy import inspect

from app import create_app, db
from config import Config


class EmptyDatabaseConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


def test_application_factory_does_not_create_schema_implicitly():
    app = create_app(EmptyDatabaseConfig)
    with app.app_context():
        assert inspect(db.engine).get_table_names() == []


def test_flask_migrate_cli_is_registered():
    app = create_app(EmptyDatabaseConfig)
    result = app.test_cli_runner().invoke(args=['db', '--help'])
    assert result.exit_code == 0
    assert 'upgrade' in result.output

import os
import secrets
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    _env = os.getenv('FLASK_ENV', os.getenv('ENV', 'development')).lower()
    _is_prod = _env in {'production', 'prod'}

    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

    if _is_prod:
        if not SECRET_KEY:
            raise RuntimeError(
                'CRITICAL SECURITY ERROR: SECRET_KEY must be explicitly set via environment variables in production mode.'
            )
        if not JWT_SECRET_KEY:
            raise RuntimeError(
                'CRITICAL SECURITY ERROR: JWT_SECRET_KEY must be explicitly set via environment variables in production mode.'
            )
    else:
        SECRET_KEY = SECRET_KEY or secrets.token_hex(32)
        JWT_SECRET_KEY = JWT_SECRET_KEY or secrets.token_hex(32)

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'app.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': int(os.getenv('DB_POOL_RECYCLE', '280')),
    }
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_DEFAULT_LIMITS = [
        limit.strip()
        for limit in os.getenv(
            'RATELIMIT_DEFAULT_LIMITS', '20000 per day;2000 per hour'
        ).split(';')
        if limit.strip()
    ]
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv('CORS_ORIGINS', '' if _is_prod else '*').split(',')
        if origin.strip()
    ]
    if _is_prod and (not CORS_ORIGINS or '*' in CORS_ORIGINS):
        raise RuntimeError(
            'CRITICAL SECURITY ERROR: CORS_ORIGINS must list explicit allowed origins in production mode.'
        )
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024)))
    API_TITLE = os.getenv('API_TITLE', 'DistribuFlow ERP API v1.1')
    API_VERSION = os.getenv('API_VERSION', '1.1')
    API_DESCRIPTION = os.getenv('API_DESCRIPTION', 'Modular REST API for DistribuFlow ERP - Inventory Management System')
    OPENAPI_VERSION = os.getenv('OPENAPI_VERSION', '3.0.2')
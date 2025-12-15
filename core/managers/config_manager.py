import os
import secrets
from sqlalchemy.pool import NullPool


class ConfigManager:
    def __init__(self, app):
        self.app = app

    def load_config(self, config_name="development"):
        # If config_name is not provided, use the environment variable FLASK_ENV
        if config_name is None:
            config_name = os.getenv("FLASK_ENV", "development")

        # Load configuration
        if config_name == "testing":
            self.app.config.from_object(TestingConfig)
        elif config_name == "production":
            self.app.config.from_object(ProductionConfig)
        else:
            self.app.config.from_object(DevelopmentConfig)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_bytes())
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('MARIADB_USER', 'default_user')}:"
        f"{os.getenv('MARIADB_PASSWORD', 'default_password')}@"
        f"{os.getenv('MARIADB_HOSTNAME', 'localhost')}:"
        f"{os.getenv('MARIADB_PORT', '3306')}/"
        f"{os.getenv('MARIADB_DATABASE', 'default_db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Conservative engine options to respect low max_user_connections in shared DBs
    _pool_class = os.getenv("DB_POOL_CLASS", "queue").lower()
    if _pool_class == "null":
        # NullPool: do not pass pool_* size/overflow/timeout options (they are invalid)
        SQLALCHEMY_ENGINE_OPTIONS = {
            "poolclass": NullPool,
            # pre_ping is still useful to validate connections on open
            "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
        }
    else:
        # QueuePool (default): keep pool constrained for shared DBs
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_size": int(os.getenv("DB_POOL_SIZE", "1")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "0")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
            "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "10")),
        }
    TIMEZONE = "Europe/Madrid"
    TEMPLATES_AUTO_RELOAD = True
    UPLOAD_FOLDER = "uploads"


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{os.getenv('MARIADB_USER', 'default_user')}:"
        f"{os.getenv('MARIADB_PASSWORD', 'default_password')}@"
        f"{os.getenv('MARIADB_HOSTNAME', 'localhost')}:"
        f"{os.getenv('MARIADB_PORT', '3306')}/"
        f"{os.getenv('MARIADB_TEST_DATABASE', 'default_db')}"
    )
    WTF_CSRF_ENABLED = False
    # In testing, avoid queue timeouts by not holding connections
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": NullPool,
        "pool_pre_ping": True,
    }


class ProductionConfig(Config):
    DEBUG = False

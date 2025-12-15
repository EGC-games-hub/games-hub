import os
import secrets


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
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Keep pool small to avoid exhausting provider limits (e.g., 5)
        "pool_size": int(os.getenv("DB_POOL_SIZE", "2")),
        # Do not allow going beyond pool_size
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "0")),
        # Recycle connections periodically to avoid stale server-side connections
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
        # Validate connections from pool before using them
        "pool_pre_ping": os.getenv("DB_POOL_PRE_PING", "true").lower() == "true",
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


class ProductionConfig(Config):
    DEBUG = False

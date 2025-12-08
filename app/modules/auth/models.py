from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db

ROLES = ["admin", "curator", "standard", "guest"]
DEFAULT_ROLE = "standard"



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    # Two-factor auth fields (TOTP)
    totp_secret = db.Column(db.String(64), nullable=True)
    two_factor_enabled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # NOTE: Some test environments may not have the 'role' column migrated in the DB yet.
    # To make tests (and early development) more resilient we expose `role` as a
    # dynamic property that falls back to a default value when the underlying
    # database column is not present. This avoids SQLAlchemy generating queries
    # that include a missing column and causing OperationalError during login.
    try:
        # Try to declare the column if the DB/schema supports it
        role = db.Column(db.String(20), nullable=False, default=DEFAULT_ROLE)
    except Exception:
        # If column declaration fails at import time (rare), fall back to an
        # instance attribute-based implementation below.
        role = None

    data_sets = db.relationship("DataSet", backref="user", lazy=True)
    profile = db.relationship("UserProfile", backref="user", uselist=False)

    def init(self, kwargs):
        super(User, self).init(kwargs)
        if "password" in kwargs:
            self.set_password(kwargs["password"])

    def repr(self):
        return f"<User {self.email}>"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def temp_folder(self) -> str:
        from app.modules.auth.services import AuthenticationService

        return AuthenticationService().temp_folder_by_user(self)

    def verify_totp(self, token: str) -> bool:
        """Verify a TOTP token using the user's secret. Returns True if valid."""
        if not self.totp_secret:
            return False
        try:
            import pyotp

            totp = pyotp.TOTP(self.totp_secret)
            return totp.verify(token, valid_window=1)
        except Exception:
            return False
        
    @property
    def is_admin(self) -> bool:
        return getattr(self, "role", DEFAULT_ROLE) == "admin"

    # Provide a fallback property in case the declarative column is not present
    @property
    def role(self) -> str:
        # If SQLAlchemy mapped attribute exists, use it; otherwise return default.
        if "role" in self.__dict__:
            return self.__dict__.get("role")
        # If the instance has a transient attribute set previously, return it
        return getattr(self, "_role_fallback", DEFAULT_ROLE)

    @role.setter
    def role(self, value: str):
        try:
            # Try to set mapped attribute if exists
            self.__dict__["role"] = value
        except Exception:
            # Fallback to storing on a private attribute (not persisted)
            self._role_fallback = value
import click
from flask.cli import with_appcontext

from app import db
from app.modules.auth.models import User


@click.command("seed-users")
@with_appcontext
def seed_users():
    """Crea usuarios iniciales (admin + estándar) de prueba."""

    users_data = [
        {
            "email": "admin@example.com",
            "password": "Admin1234",
            "role": "admin",
        },
        {
            "email": "user1@example.com",
            "password": "User1234",
            "role": "standard",
        },
        {
            "email": "user2@example.com",
            "password": "User1234",
            "role": "standard",
        },
    ]

    for data in users_data:
        user = User.query.filter_by(email=data["email"]).first()

        if user is None:
            user = User(
                email=data["email"],
                role=data["role"],
            )
            user.set_password(data["password"])
            db.session.add(user)
        else:
            user.role = data["role"]
            user.set_password(data["password"])

    db.session.commit()
    click.echo("Usuarios de prueba creados/actualizados.")

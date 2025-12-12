from app.modules.auth.models import User
from app.modules.profile.models import UserProfile
from core.seeders.BaseSeeder import BaseSeeder


class AuthSeeder(BaseSeeder):

    priority = 1  # Higher priority

    def run(self):

        # ---- 1) Definición de usuarios ----
        seed_users = [
            {
                "email": "admin@example.com",
                "password": "1234",
                "role": "admin",
                "name": "System",
                "surname": "Administrator",
                "affiliation": "Platform Admin",
            },
            {
                "email": "curator@example.com",
                "password": "1234",
                "role": "curator",
                "name": "Data",
                "surname": "Curator",
                "affiliation": "Research Group",
            },
            {
                "email": "user1@example.com",
                "password": "1234",
                "role": "standard",
                "name": "John",
                "surname": "Doe",
                "affiliation": "University",
            },
            {
                "email": "user2@example.com",
                "password": "1234",
                "role": "standard",
                "name": "Jane",
                "surname": "Doe",
                "affiliation": "University",
            },
        ]

        created_users = []

        # ---- 2) Crear / actualizar usuarios ----
        for data in seed_users:

            user = User.query.filter_by(email=data["email"]).first()

            if user is None:
                # Crear usuario nuevo
                user = User(
                    email=data["email"],
                    role=data["role"],
                )
                user.set_password(data["password"])
                self.db.session.add(user)
            else:
                # Actualizar usuario existente
                user.role = data["role"]
                user.set_password(data["password"])

            created_users.append((user, data))

        self.db.session.commit()

        # ---- 3) Crear / actualizar perfiles ----
        for user, data in created_users:

            profile = UserProfile.query.filter_by(user_id=user.id).first()

            if profile is None:
                profile = UserProfile(
                    user_id=user.id,
                    name=data["name"],
                    surname=data["surname"],
                    affiliation=data["affiliation"],
                    orcid="",
                )
                self.db.session.add(profile)
            else:
                profile.name = data["name"]
                profile.surname = data["surname"]
                profile.affiliation = data["affiliation"]

        self.db.session.commit()

        print("AuthSeeder → Usuarios y perfiles creados/actualizados correctamente.")

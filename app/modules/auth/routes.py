from flask import redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, SignupForm
from app.modules.auth.services import AuthenticationService
from app.modules.profile.services import UserProfileService
from flask import session, send_file, flash
from io import BytesIO

from app.modules.auth.forms import TwoFactorForm

authentication_service = AuthenticationService()
user_profile_service = UserProfileService()


@auth_bp.route("/signup/", methods=["GET", "POST"])
def show_signup_form():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        if not authentication_service.is_email_available(email):
            return render_template("auth/signup_form.html", form=form, error=f"Email {email} in use")

        try:
            user = authentication_service.create_with_profile(**form.data)
        except Exception as exc:
            return render_template("auth/signup_form.html", form=form, error=f"Error creating user: {exc}")

        # Log user
        login_user(user, remember=True)
        return redirect(url_for("public.index"))

    return render_template("auth/signup_form.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        result = authentication_service.login(form.email.data, form.password.data, remember=form.remember_me.data)
        if result == True:
            return redirect(url_for("public.index"))

        if result == "otp_required":
            # store the user id temporarily in session and redirect to verification
            user = authentication_service.repository.get_by_email(form.email.data)
            session["pre_2fa_user_id"] = user.id
            session["remember_me"] = form.remember_me.data
            return redirect(url_for("auth.two_factor_verify"))

        return render_template("auth/login_form.html", form=form, error="Invalid credentials")

    return render_template("auth/login_form.html", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.index"))


@auth_bp.route("/2fa/verify", methods=["GET", "POST"])
def two_factor_verify():
    # Page where user submits the TOTP code after initial password check
    form = TwoFactorForm()
    user_id = session.get("pre_2fa_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))

    user = authentication_service.repository.get_by_id(user_id)
    if request.method == "POST" and form.validate_on_submit():
        token = form.token.data.strip()
        if user and user.verify_totp(token):
            # finalise login
            login_user(user, remember=session.get("remember_me", False))
            session.pop("pre_2fa_user_id", None)
            session.pop("remember_me", None)
            return redirect(url_for("public.index"))
        flash("Invalid authentication code", "danger")

    return render_template("auth/2fa_verify.html", form=form)


@auth_bp.route("/2fa/setup", methods=["GET", "POST"])
def two_factor_setup():
    # Allow authenticated users to enable 2FA
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login"))

    # If user already has secret, show the provisioning QR and secret
    user = current_user
    form = TwoFactorForm()

    if not getattr(user, "totp_secret", None):
        # generate secret and persist temporarily
        import pyotp

        secret = pyotp.random_base32()
    user.totp_secret = secret
    # do not enable until confirmed
    user.two_factor_enabled = False
    authentication_service.repository.session.add(user)
    authentication_service.repository.session.commit()

    # Build provisioning URI
    import pyotp

    uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(name=user.email, issuer_name="Games Hub")

    return render_template("auth/2fa_setup.html", uri=uri, secret=user.totp_secret, form=form)


@auth_bp.route("/2fa/qrcode")
def two_factor_qrcode():
    # Return a PNG QR code for the provisioning URI
    if not current_user.is_authenticated:
        return ("", 401)
    user = current_user
    if not getattr(user, "totp_secret", None):
        return ("No 2FA secret configured", 404)

    import qrcode

    import pyotp

    uri = pyotp.totp.TOTP(user.totp_secret).provisioning_uri(name=user.email, issuer_name="Games Hub")
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@auth_bp.route("/2fa/confirm", methods=["POST"])
def two_factor_confirm():
    # Endpoint to confirm and enable 2FA after scanning
    if not current_user.is_authenticated:
        return ("", 401)

    form = TwoFactorForm()
    if form.validate_on_submit():
        token = form.token.data.strip()
        user = current_user
        if user.verify_totp(token):
            user.two_factor_enabled = True
            authentication_service.repository.session.add(user)
            authentication_service.repository.session.commit()
            flash("Two-factor authentication enabled.", "success")
            return redirect(url_for("profile.edit_profile"))
        flash("Invalid authentication code.", "danger")

    return redirect(url_for("auth.two_factor_setup"))
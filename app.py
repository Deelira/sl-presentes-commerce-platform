"""Application factory."""

import logging
import os
from datetime import datetime

from flask import Flask, jsonify, render_template
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text

from config import Config, is_placeholder
from models import db
from models.user import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

login_manager = LoginManager()
csrf = CSRFProtect()

mail = Mail()

migrate = Migrate()


def _get_admin_credentials():
    email = os.environ.get("INIT_ADMIN_EMAIL")
    password = os.environ.get("INIT_ADMIN_PASSWORD")

    if not email or not password or is_placeholder(email) or is_placeholder(password):
        logger.warning(
            "Admin inicial não criado. Defina INIT_ADMIN_EMAIL e INIT_ADMIN_PASSWORD no .env."
        )
        return None

    return email, password


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)
    app.config["UPLOAD_FOLDER"].mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Blueprints
    from routes.shop import shop_bp
    from routes.auth import auth_bp
    from routes.cart import cart_bp
    from routes.checkout import checkout_bp
    from routes.account import account_bp
    from routes.admin import admin_bp

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(checkout_bp, url_prefix="/checkout")
    app.register_blueprint(account_bp, url_prefix="/account")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.context_processor
    def inject_globals():
        from flask import session

        cart = session.get("cart", {})
        cart_count = sum(item["qty"] for item in cart.values()) if cart else 0

        try:
            categories = Category.query.order_by(Category.name).all()
        except:
            categories = []

        return {
            "STORE_NAME": app.config["STORE_NAME"],
            "STORE_TAGLINE": app.config["STORE_TAGLINE"],
            "CURRENCY": app.config["CURRENCY"],
            "nav_categories": categories,
            "cart_count": cart_count,
        }

    @app.get("/healthz")
    def healthz():
        try:
            db.session.execute(text("SELECT 1"))
            database_status = "ok"
            status_code = 200
        except Exception:
            database_status = "error"
            status_code = 503

        payload = {
            "status": "ok" if database_status == "ok" else "error",
            "app_env": app.config.get("APP_ENV", "unknown"),
            "database": database_status,
            "admin_configured": admin_credentials is not None,
        }

        return jsonify(payload), status_code

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    # Jinja filters
    @app.template_filter("brl")
    def brl_filter(value):
        """Formata valor para moeda brasileira"""
        if value is None:
            return "R$ 0,00"
        try:
            # Formatar com 2 casas decimais
            return (
                f"R$ {float(value):,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        except (ValueError, TypeError):
            return "R$ 0,00"

    @app.template_filter("timeago")
    def timeago_filter(date):
        """Formato amigável de tempo"""
        if not date:
            return "Recentemente"

        now = datetime.utcnow()
        diff = now - date

        if diff.days > 30:
            months = diff.days // 30
            return f"{months} {'mês' if months == 1 else 'meses'} atrás"
        elif diff.days > 7:
            weeks = diff.days // 7
            return f"{weeks} {'semana' if weeks == 1 else 'semanas'} atrás"
        elif diff.days > 0:
            return f"{diff.days} {'dia' if diff.days == 1 else 'dias'} atrás"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} {'hora' if hours == 1 else 'horas'} atrás"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} {'minuto' if minutes == 1 else 'minutos'} atrás"
        else:
            return "Agora mesmo"

    from models.category import Category
    from models.product import Product
    from models.user import User

    admin_credentials = _get_admin_credentials()

    with app.app_context():
        db.create_all()

        if admin_credentials:
            admin_email, admin_password = admin_credentials
            admin_exists = User.query.filter_by(email=admin_email).first()

            if not admin_exists:
                admin = User(name="Administrador", email=admin_email, role="admin")
                admin.set_password(admin_password)
                db.session.add(admin)
                db.session.commit()
                logger.info("Administrador inicial criado com sucesso.")

    return app


application = create_app()

if __name__ == "__main__":
    application.run(
        debug=application.config.get("DEBUG", False),
        host="0.0.0.0",
        port=5000,
    )

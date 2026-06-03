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


def _create_default_users():
    """Cria usuários padrão para teste se não existirem"""
    
    # Usuário Administrador
    admin_email = os.environ.get("INIT_ADMIN_EMAIL", "admin@exemplo.com")
    admin_password = os.environ.get("INIT_ADMIN_PASSWORD", "admin123")
    
    if not is_placeholder(admin_email) and not is_placeholder(admin_password):
        admin_exists = User.query.filter_by(email=admin_email).first()
        if not admin_exists:
            admin = User(
                name="Administrador", 
                email=admin_email, 
                role="admin"
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            logger.info(f"Administrador criado: {admin_email}")
    else:
        logger.warning("Admin não criado: credenciais inválidas ou não configuradas")
    
    # Usuário Comum (para testes)
    user_email = os.environ.get("TEST_USER_EMAIL", "cliente@exemplo.com")
    user_password = os.environ.get("TEST_USER_PASSWORD", "cliente123")
    
    if not is_placeholder(user_email) and not is_placeholder(user_password):
        user_exists = User.query.filter_by(email=user_email).first()
        if not user_exists:
            user = User(
                name="Cliente Teste", 
                email=user_email, 
                role="user"
            )
            user.set_password(user_password)
            db.session.add(user)
            logger.info(f"Usuário comum criado: {user_email}")
    else:
        logger.warning("Usuário comum não criado: credenciais inválidas ou não configuradas")
    
    db.session.commit()


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
            from models.category import Category
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

        # Verificar se admin foi criado
        admin_exists = False
        try:
            from models.user import User
            admin_exists = User.query.filter_by(role="admin").first() is not None
        except:
            pass

        payload = {
            "status": "ok" if database_status == "ok" else "error",
            "app_env": app.config.get("APP_ENV", "unknown"),
            "database": database_status,
            "admin_configured": admin_exists,
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

    # Criar usuários padrão dentro do contexto da aplicação
    with app.app_context():
        db.create_all()
        _create_default_users()  # ← AQUI: chamando a função correta

    return app


# Cria a aplicação para o gunicorn
application = create_app()

if __name__ == "__main__":
    application.run(
        debug=application.config.get("DEBUG", False),
        host="0.0.0.0",
        port=5000,
    )

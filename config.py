import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UNSAFE_SECRET_VALUES = {
    "change-me-in-production-please",
    "troque-esta-chave-em-producao",
    "dev-local-secret-change-me",
}


def _normalize_database_uri(uri: str | None) -> str:
    if not uri:
        return f"sqlite:///{BASE_DIR / 'instance' / 'sl-presentes.db'}"

    if uri.startswith("sqlite:///") and not uri.startswith("sqlite:////"):
        relative_path = uri.replace("sqlite:///", "", 1)
        absolute_path = (BASE_DIR / relative_path).resolve()
        return f"sqlite:///{absolute_path}"

    return uri


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, default)
    if value is None:
        return None

    return value.strip()


def is_placeholder(value: str | None) -> bool:
    if value is None:
        return True

    return value.strip().lower() in UNSAFE_SECRET_VALUES


class Config:
    APP_ENV = get_env("FLASK_ENV", "development")
    DEBUG = get_env("FLASK_DEBUG", "true" if APP_ENV == "development" else "false").lower() == "true"

    SECRET_KEY = get_env("SECRET_KEY") or (
        "dev-local-secret-change-me" if APP_ENV != "production" else None
    )

    SQLALCHEMY_DATABASE_URI = _normalize_database_uri(get_env("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = 3600
    UPLOAD_FOLDER = BASE_DIR / "static" / "images" / "uploads"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = APP_ENV == "production"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = APP_ENV == "production"
    PIX_WEBHOOK_SECRET = get_env("PIX_WEBHOOK_SECRET")
    
    # 🔥 Configurações Mercado Pago
    MP_ACCESS_TOKEN = get_env("MP_ACCESS_TOKEN")
    MP_PUBLIC_KEY = get_env("MP_PUBLIC_KEY")
    MP_USER_ID = get_env("MP_USER_ID")
    MERCADO_PAGO_NOTIFICATION_URL = get_env("MERCADO_PAGO_NOTIFICATION_URL")
    
    STORE_NAME = "SL PRESENTES"
    STORE_TAGLINE = "Tudo para surpreender quem você ama!"
    CURRENCY = "R$"


# Configurações de e-mail - GMAIL
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = "seu-email@gmail.com"  # Seu e-mail
MAIL_PASSWORD = "sua-senha-de-app"  # Senha de app do Gmail
MAIL_DEFAULT_SENDER = "seu-email@gmail.com"

# Como criar senha de app no Gmail:

# Acesse: https://myaccount.google.com/security

# Ative "Verificação em duas etapas"

# Vá em "Senhas de app"

# Selecione "E-mail" e "Windows Computer"

# Copie a senha de 16 dígitos gerada

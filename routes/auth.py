import re
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from auth.forms import ForgotForm, LoginForm, RegisterForm, ResetForm, VerifyCPFForm
from models import db
from models.user import User

# Use o mesmo nome do blueprint que você já tinha
auth_bp = Blueprint("auth", __name__)
_reset_tokens = {}  # in-memory simples (produção: tabela ou cache)
RESET_TOKEN_TTL = timedelta(hours=1)


# Função auxiliar para limpar CPF
def limpar_cpf(cpf):
    """Remove pontos, traços e espaços do CPF"""
    if not cpf:
        return ""
    return re.sub(r"[^0-9]", "", str(cpf))


def _store_reset_token(user_id):
    token = secrets.token_urlsafe(24)
    _reset_tokens[token] = {
        "user_id": user_id,
        "expires_at": datetime.utcnow() + RESET_TOKEN_TTL,
    }
    return token


def _consume_reset_token(token):
    token_data = _reset_tokens.get(token)

    if not token_data:
        return None

    if token_data.get("expires_at", datetime.utcnow()) <= datetime.utcnow():
        _reset_tokens.pop(token, None)
        return None

    _reset_tokens.pop(token, None)
    return token_data.get("user_id")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("shop.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data) and user.is_active_flag:
            login_user(user, remember=form.remember.data)
            flash("Bem-vindo de volta!", "success")
            next_url = request.args.get("next")
            if user.is_admin and not next_url:
                return redirect(url_for("admin.dashboard"))
            return redirect(next_url or url_for("shop.home"))
        flash("Credenciais inválidas.", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()

        # Verifica se email já existe
        if User.query.filter_by(email=email).first():
            flash("Email já cadastrado.", "warning")
        else:
            # Limpa o CPF
            cpf_limpo = limpar_cpf(form.cpf.data)

            # Verifica se CPF já existe
            if User.query.filter_by(cpf=cpf_limpo).first():
                flash("CPF já cadastrado.", "warning")
            else:
                u = User(
                    name=form.name.data.strip(),
                    email=email,
                    phone=form.phone.data,
                    cpf=cpf_limpo,  # Adiciona o CPF
                )
                u.set_password(form.password.data)
                db.session.add(u)
                db.session.commit()
                login_user(u)
                flash("Conta criada com sucesso!", "success")
                return redirect(url_for("shop.home"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da conta.", "info")
    return redirect(url_for("shop.home"))


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    """Primeira etapa: digitar email"""
    if current_user.is_authenticated:
        return redirect(url_for("shop.home"))

    form = ForgotForm()
    erro = None

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if user:
            # Salva o email na sessão para próxima etapa
            session["reset_email"] = email
            # Redireciona para verificação de CPF
            return redirect(url_for("auth.verificar_cpf"))
        else:
            erro = "E-mail não encontrado no sistema"

    return render_template("auth/forgot.html", form=form, erro=erro)


@auth_bp.route("/verificar-cpf", methods=["GET", "POST"])
def verificar_cpf():
    """Segunda etapa: verificar CPF do usuário"""
    if current_user.is_authenticated:
        return redirect(url_for("shop.home"))

    # Verifica se tem email na sessão
    if "reset_email" not in session:
        return redirect(url_for("auth.forgot"))

    email = session["reset_email"]
    user = User.query.filter_by(email=email).first()

    if not user:
        session.pop("reset_email", None)
        return redirect(url_for("auth.forgot"))

    form = VerifyCPFForm()
    erro = None

    if form.validate_on_submit():
        cpf_digitado = limpar_cpf(form.cpf.data)
        cpf_usuario = limpar_cpf(user.cpf) if user.cpf else ""

        if cpf_digitado == cpf_usuario:
            token = _store_reset_token(user.id)
            session["reset_verified"] = True
            session.pop("reset_email", None)
            return redirect(url_for("auth.reset", token=token))
        else:
            erro = "CPF não confere com o usuário informado"

    return render_template(
        "auth/verificar_cpf.html", form=form, usuario=user, erro=erro
    )


@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    """Terceira etapa: redefinir senha"""
    uid = _consume_reset_token(token)

    if not uid:
        flash("Token inválido ou expirado.", "danger")
        return redirect(url_for("auth.forgot"))

    form = ResetForm()
    if form.validate_on_submit():
        user = db.session.get(User, uid)
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            session.pop("reset_verified", None)
            flash("Senha redefinida com sucesso.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Usuário não encontrado.", "danger")
            return redirect(url_for("auth.forgot"))

    return render_template("auth/reset.html", form=form)

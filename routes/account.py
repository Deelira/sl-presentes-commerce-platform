from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from auth.forms import PasswordForm, ProfileForm
from models import db
from models.order import Order

account_bp = Blueprint("account", __name__)


@account_bp.route("/")
@login_required
def index():
    orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("shop/account.html", orders=orders)


@account_bp.route("/pedido/<code>")
@login_required
def order_detail(code):
    order = Order.query.filter_by(code=code).first_or_404()
    if order.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template("shop/order_detail.html", order=order)


@account_bp.route("/editar", methods=["GET", "POST"])
@login_required
def edit_profile():
    profile_form = ProfileForm()
    password_form = PasswordForm()

    if request.method == "GET":
        profile_form.name.data = current_user.name
        profile_form.email.data = current_user.email
        profile_form.phone.data = current_user.phone or ""
        profile_form.cpf.data = current_user.cpf or ""

    if request.method == "POST":
        is_password_action = any(
            request.form.get(field)
            for field in ("current_password", "new_password", "confirm_password")
        )

        if is_password_action:
            if password_form.validate_on_submit():
                if not current_user.check_password(password_form.current_password.data):
                    flash("Senha atual incorreta.", "danger")
                else:
                    current_user.set_password(password_form.new_password.data)
                    db.session.commit()
                    flash("Senha atualizada com sucesso.", "success")
                    return redirect(url_for("account.edit_profile"))
        elif profile_form.validate_on_submit():
            current_user.name = profile_form.name.data
            current_user.email = profile_form.email.data
            current_user.phone = profile_form.phone.data or None
            current_user.cpf = profile_form.cpf.data or None
            db.session.commit()
            flash("Informações de contato atualizadas com sucesso.", "success")
            return redirect(url_for("account.edit_profile"))

    return render_template(
        "shop/account_edit.html",
        profile_form=profile_form,
        password_form=password_form,
    )

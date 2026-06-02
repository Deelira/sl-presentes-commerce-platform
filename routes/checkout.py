import hashlib
import hmac
import io

from app import csrf
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for, abort, send_file
from flask_login import current_user, login_required

from admin.forms import CheckoutForm
from models import db
from models.order import Order, OrderItem
from models.product import Product
from services import cart as cart_service
from services.payment import create_pix_charge
from utils.helpers import generate_order_code

checkout_bp = Blueprint("checkout", __name__)


def _webhook_signature_is_valid(payload: bytes) -> bool:
    secret = current_app.config.get("PIX_WEBHOOK_SECRET")
    if not secret:
        return False

    signature = request.headers.get("X-Webhook-Signature", "").strip()
    if not signature:
        return False

    expected = hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


@checkout_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    cart_service.sync_with_database()
    items = cart_service.items()
    if not items:
        flash("Seu carrinho está vazio.", "warning")
        return redirect(url_for("shop.products"))

    form = CheckoutForm()

    if not form.is_submitted():
        form.customer_name.data = current_user.name
        if getattr(current_user, "cpf", None):
            form.cpf.data = current_user.cpf
        form.phone.data = current_user.phone or ""

    if form.validate_on_submit():
        try:
            with db.session.begin_nested():
                for it in items:
                    prod = db.session.get(Product, it["id"])
                    if not prod:
                        flash(f"Produto '{it['name']}' não encontrado.", "danger")
                        return redirect(url_for("cart.view"))

                    if prod.stock < it["qty"]:
                        flash(
                            f"Estoque insuficiente para '{prod.name}'. Disponível: {prod.stock} unidades.",
                            "danger",
                        )
                        return redirect(url_for("cart.view"))

                order = Order(
                    code=generate_order_code(),
                    user_id=current_user.id,
                    total=cart_service.total(),
                    customer_name=form.customer_name.data,
                    cpf=form.cpf.data,
                    phone=form.phone.data,
                    cep=form.cep.data,
                    address=form.address.data,
                    complement=form.complement.data,
                    number=form.number.data,
                    city=form.city.data,
                    state=form.state.data,
                    payment_method="PIX",
                    status="pendente",
                )
                db.session.add(order)
                db.session.flush()

                for it in items:
                    prod = db.session.get(Product, it["id"])
                    prod.stock -= it["qty"]

                    db.session.add(
                        OrderItem(
                            order_id=order.id,
                            product_id=prod.id,
                            product_name=prod.name,
                            sku=prod.sku,
                            unit_price=it["price"],
                            supplier_price=prod.supplier_price or 0,
                            quantity=it["qty"],
                        )
                    )

                if not current_user.cpf and form.cpf.data:
                    current_user.cpf = form.cpf.data
                    db.session.add(current_user)

            db.session.commit()
            cart_service.clear()
            flash("Pedido realizado com sucesso!", "success")
            return redirect(url_for("checkout.success", code=order.code))
        except Exception:
            db.session.rollback()
            flash("Não foi possível concluir o pedido. Tente novamente.", "danger")
            return redirect(url_for("cart.view"))

    return render_template(
        "shop/checkout.html", form=form, items=items, total=cart_service.total()
    )


@checkout_bp.route("/sucesso/<code>")
@login_required
def success(code):
    order = Order.query.filter_by(code=code, user_id=current_user.id).first_or_404()
    pix = create_pix_charge(order)
    # Armazena dados do pagamento no banco
    order.payment_data = pix
    db.session.commit()
    return render_template("shop/checkout_success.html", order=order, pix=pix)


@checkout_bp.route("/qrcode/<code>")
@login_required
def qrcode_image(code):
    """Serve a imagem PNG do QR code PIX."""
    from services.payment import create_pix_qrcode_image
    
    order = Order.query.filter_by(code=code, user_id=current_user.id).first_or_404()
    pix = order.payment_data or {}
    
    if not pix.get("qr_code"):
        abort(404)
    
    qr_image = create_pix_qrcode_image(pix.get("qr_code"))
    if not qr_image:
        abort(404)
    
    return send_file(
        io.BytesIO(qr_image),
        mimetype="image/png",
        as_attachment=False,
        download_name=f"qrcode_{code}.png"
    )


# 🔥 FUNÇÃO PARA CANCELAR PEDIDO E RETORNAR ESTOQUE
@checkout_bp.route("/cancelar/<int:order_id>")
@login_required
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    success, message, _ = order.cancel_and_restore_stock()

    if success:
        db.session.commit()
        flash(f"Pedido #{order.code} {message.lower()}", "success")
        return redirect(url_for("account.index"))

    flash(f"Erro: {message}", "danger")
    return redirect(url_for("account.index"))


# 🔥 WEBHOOK PARA CONFIRMAR PAGAMENTO PIX
@csrf.exempt
@checkout_bp.route("/webhook/pix", methods=["POST"])
def pix_webhook():
    """Recebe confirmação de pagamento do gateway."""
    payload = request.get_data(cache=True)

    if not _webhook_signature_is_valid(payload):
        return jsonify({"error": "assinatura inválida"}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "payload inválido"}), 400

    order_code = data.get("reference")
    status = data.get("status")

    if not order_code or not status:
        return jsonify({"error": "reference e status são obrigatórios"}), 400

    order = Order.query.filter_by(code=order_code).first()
    if not order:
        return jsonify({"error": "Order not found"}), 404

    if status == "paid":
        if order.status == "cancelado":
            return jsonify({"status": "ignored", "order_status": order.status}), 200

        order.status = "pago"
        db.session.commit()
        return jsonify({"status": "ok", "order_status": order.status}), 200

    if status == "canceled":
        if order.status == "pago":
            return jsonify({"status": "ignored", "order_status": order.status}), 200

        success, message, _ = order.cancel_and_restore_stock()
        if success:
            db.session.commit()
            return jsonify({"status": "ok", "order_status": order.status}), 200

        return jsonify(
            {"status": "ignored", "order_status": order.status, "message": message}
        ), 200

    return jsonify({"status": "ignored", "order_status": order.status}), 200

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from services import cart as cart_service
from models import db
from models.product import Product

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/")
def view():
    # 🔥 Sincroniza carrinho com banco antes de mostrar
    cart_service.sync_with_database()

    items = cart_service.items()
    total = cart_service.total()

    return render_template("shop/cart.html", items=items, total=total)


@cart_bp.route("/add/<int:product_id>", methods=["POST"])
def add(product_id):
    qty = int(request.form.get("qty", 1))

    # VALIDAÇÃO DE ESTOQUE
    product = db.session.get(Product, product_id)
    if not product:
        flash("Produto não encontrado.", "danger")
        return redirect(request.referrer or url_for("shop.home"))

    # Verifica se produto está esgotado
    if product.stock <= 0:
        flash(
            f"'{product.name}' está ESGOTADO e não pode ser adicionado ao carrinho.",
            "danger",
        )
        return redirect(request.referrer or url_for("shop.products"))

    # Verifica se quantidade solicitada é maior que o estoque
    if qty > product.stock:
        flash(
            f"⚠️ Você tentou adicionar {qty}x '{product.name}', mas só temos {product.stock} unidade(s) em estoque.",
            "warning",
        )
        return redirect(
            request.referrer or url_for("shop.product_detail", slug=product.slug)
        )

    # Verifica quantidade atual no carrinho
    current_qty = cart_service.get_quantity(product_id)
    new_total_qty = current_qty + qty

    if new_total_qty > product.stock:
        available = product.stock - current_qty
        if available <= 0:
            flash(
                f"⚠️ Você já tem {current_qty}x '{product.name}' no carrinho. Estoque esgotado!",
                "warning",
            )
        else:
            flash(
                f"⚠️ Você já tem {current_qty}x '{product.name}' no carrinho. Só é possível adicionar mais {available} unidade(s).",
                "warning",
            )
        return redirect(
            request.referrer or url_for("shop.product_detail", slug=product.slug)
        )

    cart_service.add(product_id, qty)

    # Mensagem informativa
    if new_total_qty == product.stock:
        flash(
            f"✅ {qty}x '{product.name}' adicionado! Agora você tem {new_total_qty}/{product.stock} unidades (estoque completo).",
            "success",
        )
    else:
        flash(f"✅ {qty}x '{product.name}' adicionado ao carrinho!", "success")

    return redirect(request.referrer or url_for("cart.view"))


@cart_bp.route("/update/<int:product_id>", methods=["POST"])
def update(product_id):
    qty = int(request.form.get("qty", 1))

    # VALIDAÇÃO DE ESTOQUE PARA ATUALIZAÇÃO
    product = db.session.get(Product, product_id)
    if not product:
        flash("Produto não encontrado.", "danger")
        return redirect(url_for("cart.view"))

    if qty > product.stock:
        flash(
            f"⚠️ Quantidade máxima disponível para '{product.name}' é {product.stock} unidade(s).",
            "warning",
        )
        return redirect(url_for("cart.view"))

    if qty <= 0:
        cart_service.remove(product_id)
        flash(f"'{product.name}' removido do carrinho.", "info")
        return redirect(url_for("cart.view"))

    cart_service.update(product_id, qty)
    flash("✅ Carrinho atualizado!", "success")
    return redirect(url_for("cart.view"))


@cart_bp.route("/remove/<int:product_id>", methods=["POST"])
def remove(product_id):
    product = db.session.get(Product, product_id)
    cart_service.remove(product_id)
    if product:
        flash(f"'{product.name}' removido do carrinho.", "info")
    return redirect(url_for("cart.view"))


@cart_bp.route("/clear", methods=["POST"])
def clear():
    """Limpa todo o carrinho"""
    cart_service.clear()
    flash("Carrinho esvaziado com sucesso.", "info")
    return redirect(url_for("cart.view"))


@cart_bp.route("/check-stock", methods=["GET"])
def check_stock():
    """Verifica se todos os itens no carrinho têm estoque disponível"""
    # Sincroniza antes de verificar
    cart_service.sync_with_database()

    items = cart_service.items()
    stock_issues = []

    for item in items:
        product = db.session.get(Product, item["id"])

        if not product:
            stock_issues.append(
                {
                    "name": item.get("name", "Produto desconhecido"),
                    "available": 0,
                    "requested": item.get("qty", 0),
                    "issue": "Produto não encontrado no sistema",
                }
            )
        elif product.stock <= 0:
            stock_issues.append(
                {
                    "name": product.name,
                    "available": 0,
                    "requested": item.get("qty", 0),
                    "issue": "Produto esgotado",
                }
            )
        elif product.stock < item.get("qty", 0):
            stock_issues.append(
                {
                    "name": product.name,
                    "available": product.stock,
                    "requested": item.get("qty", 0),
                    "issue": "Estoque insuficiente",
                }
            )

    return jsonify(
        {
            "has_issues": len(stock_issues) > 0,
            "issues": stock_issues,
            "total_items": len(items),
        }
    )


@cart_bp.route("/summary", methods=["GET"])
def summary():
    """Retorna resumo do carrinho (para AJAX)"""
    return jsonify(
        {
            "total_items": cart_service.count(),
            "total_value": cart_service.total(),
            "item_count": len(cart_service.items()),
        }
    )

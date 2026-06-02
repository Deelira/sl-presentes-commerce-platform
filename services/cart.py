"""Carrinho persistido em session."""

from flask import abort, session
from models import db
from models.product import Product


def _cart():
    return session.setdefault("cart", {})


def add(product_id, qty=1):
    """Adiciona produto ao carrinho"""
    cart = _cart()
    pid = str(product_id)

    if pid in cart:
        # Produto já existe no carrinho
        cart[pid]["qty"] += qty
    else:
        # Busca produto no banco
        product = db.session.get(Product, product_id)
        if not product:
            abort(404)
        cart[pid] = {
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "image": product.image_url,
            "qty": qty,
            "slug": product.slug,
            "sku": product.sku,  # 🔥 ADICIONADO
            "max_stock": product.stock,  # 🔥 ADICIONADO - estoque disponível
        }
    session.modified = True


def update(product_id, qty):
    """Atualiza quantidade do produto no carrinho"""
    cart = _cart()
    pid = str(product_id)

    if pid in cart:
        if qty <= 0:
            cart.pop(pid)
        else:
            cart[pid]["qty"] = qty
    session.modified = True


def remove(product_id):
    """Remove produto do carrinho"""
    cart = _cart()
    cart.pop(str(product_id), None)
    session.modified = True


def clear():
    """Limpa todo o carrinho"""
    session["cart"] = {}
    session.modified = True


def items():
    """Retorna lista de itens do carrinho"""
    return list(_cart().values())


def total():
    """Retorna valor total do carrinho"""
    return sum(i["price"] * i["qty"] for i in items())


def count():
    """Retorna quantidade total de itens no carrinho"""
    return sum(i["qty"] for i in items())


# 🔥 NOVAS FUNÇÕES ÚTEIS


def get_item(product_id):
    """Retorna um item específico do carrinho"""
    cart = _cart()
    return cart.get(str(product_id))


def update_stock_info(product_id, new_stock):
    """Atualiza informação de estoque no carrinho (útil após compra)"""
    cart = _cart()
    pid = str(product_id)
    if pid in cart:
        cart[pid]["max_stock"] = new_stock
        session.modified = True


def has_item(product_id):
    """Verifica se produto está no carrinho"""
    return str(product_id) in _cart()


def get_quantity(product_id):
    """Retorna quantidade de um produto no carrinho"""
    item = get_item(product_id)
    return item["qty"] if item else 0


def sync_with_database():
    """Sincroniza carrinho com banco de dados (atualiza preços e estoque)"""
    cart = _cart()
    modified = False

    for pid, item in list(cart.items()):
        product = db.session.get(Product, int(pid))
        if not product or product.stock <= 0:
            # Produto não existe mais ou está esgotado
            cart.pop(pid)
            modified = True
        else:
            # Atualiza informações do produto
            if item.get("price") != float(product.price):
                item["price"] = float(product.price)
                modified = True
            if item.get("max_stock") != product.stock:
                item["max_stock"] = product.stock
                # Se a quantidade no carrinho exceder o estoque, ajusta
                if item["qty"] > product.stock:
                    item["qty"] = product.stock
                modified = True

    if modified:
        session.modified = True


def to_dict():
    """Retorna carrinho completo como dicionário (para APIs)"""
    return {
        "items": items(),
        "total": total(),
        "count": count(),
        "item_count": len(items()),
    }

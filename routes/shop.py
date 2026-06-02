from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    flash,
    redirect,
    url_for,
    session,
    jsonify,
)
from flask_login import login_required, current_user
from sqlalchemy import or_, func, and_
from models.product import Product
from models.category import Category
from models.order import Order
from models.order_request import OrderRequest
from models.order import OrderItem  # Importando OrderItem do mesmo arquivo
from models import db
from flask_mail import Message

shop_bp = Blueprint("shop", __name__)


@shop_bp.route("/")
def home():
    # 🔥 Mostrar produtos mesmo sem estoque (com badge esgotado)
    featured = (
        Product.query.filter(Product.is_active == True)  # Removeu o "stock > 0"
        .order_by(func.random())
        .limit(8)
        .all()
    )

    latest = (
        Product.query.filter(Product.is_active == True)  # Removeu o "stock > 0"
        .order_by(func.random())
        .limit(8)
        .all()
    )

    # Produtos mais vendidos para mostrar na home (aleatório entre os mais vendidos)
    try:
        top_selling_data = (
            db.session.query(
                Product,
                func.coalesce(func.sum(OrderItem.quantity), 0).label("total_sold"),
            )
            .outerjoin(OrderItem, OrderItem.product_id == Product.id)
            .outerjoin(Order, Order.id == OrderItem.order_id)
            .filter(
                Product.is_active == True,
                Product.stock > 0,
                Order.status
                == "entregue",  # Apenas pedidos entregues contam como vendidos
            )
            .group_by(Product.id)
            .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
            .limit(8)
            .all()
        )

        top_selling = [item[0] for item in top_selling_data]
        # Embaralhar os mais vendidos para não ficar sempre igual
        import random

        random.shuffle(top_selling)
    except Exception as e:
        print(f"Erro ao buscar mais vendidos: {e}")
        top_selling = []

    categories = Category.query.all()
    nav_categories = Category.query.all()

    return render_template(
        "shop/home.html",
        featured=featured,
        latest=latest,
        top_selling=top_selling,
        categories=categories,
        nav_categories=nav_categories,
    )


@shop_bp.route("/produtos")
def products():
    q = request.args.get("q", "").strip()
    cat = request.args.get("cat")
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "random")

    # 🔥 CORREÇÃO: Remover a condição "stock > 0" para mostrar todos os produtos
    query = Product.query.filter(Product.is_active == True)  # Removeu o "stock > 0"

    # Aplicar filtros de busca
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Product.name.ilike(like), Product.description.ilike(like))
        )

    # Aplicar filtro de categoria
    current_category = None
    if cat:
        current_category = Category.query.filter_by(slug=cat).first()
        if current_category:
            query = query.filter_by(category_id=current_category.id)

    # Aplicar ordenação
    if sort == "popular":
        query = (
            query.outerjoin(OrderItem, OrderItem.product_id == Product.id)
            .outerjoin(Order, Order.id == OrderItem.order_id)
            .filter(or_(Order.status == "entregue", Order.status == None))
            .group_by(Product.id)
            .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
        )
    elif sort == "random":
        query = query.order_by(func.random())
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Product.created_at.asc())
    elif sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "name_asc":
        query = query.order_by(Product.name.asc())
    elif sort == "name_desc":
        query = query.order_by(Product.name.desc())
    elif sort == "stock_asc":
        query = query.order_by(Product.stock.asc())
    elif sort == "stock_desc":
        query = query.order_by(Product.stock.desc())
    else:
        query = query.order_by(func.random())

    pagination = query.paginate(page=page, per_page=12, error_out=False)

    nav_categories = Category.query.all()

    return render_template(
        "shop/products.html",
        pagination=pagination,
        q=q,
        current_cat=cat,
        current_category=current_category,
        sort=sort,
        nav_categories=nav_categories,
    )


@shop_bp.route("/produto/<slug>")
def product_detail(slug):
    # 🔥 Remover "stock > 0" para mostrar produto mesmo esgotado
    product = Product.query.filter(
        Product.slug == slug,
        Product.is_active == True,
        # Removeu Product.stock > 0
    ).first_or_404()

    # Produtos relacionados - também pode mostrar esgotados
    related = (
        Product.query.filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.is_active == True,
            # Removeu Product.stock > 0
        )
        .order_by(func.random())
        .limit(4)
        .all()
    )

    nav_categories = Category.query.all()

    return render_template(
        "shop/product_detail.html",
        product=product,
        related=related,
        nav_categories=nav_categories,
    )


@shop_bp.route("/categoria/<slug>")
def category(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()

    # Buscar produtos da categoria com ordenação padrão aleatória
    sort = request.args.get("sort", "random")  # MUDADO: padrão aleatório

    query = Product.query.filter(
        and_(
            Product.category_id == cat.id, Product.is_active == True, Product.stock > 0
        )
    )

    # Aplicar ordenação
    if sort == "popular":
        query = (
            query.outerjoin(OrderItem, OrderItem.product_id == Product.id)
            .outerjoin(Order, Order.id == OrderItem.order_id)
            .filter(or_(Order.status == "entregue", Order.status == None))
            .group_by(Product.id)
            .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
        )
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    elif sort == "oldest":
        query = query.order_by(Product.created_at.asc())
    elif sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "name_asc":
        query = query.order_by(Product.name.asc())
    elif sort == "name_desc":
        query = query.order_by(Product.name.desc())
    elif sort == "random":
        query = query.order_by(func.random())
    else:
        # Padrão: ordem aleatória
        query = query.order_by(func.random())

    # Para categoria, também podemos usar paginação se houver muitos produtos
    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=12, error_out=False)

    nav_categories = Category.query.all()

    return render_template(
        "shop/category.html",
        category=cat,
        pagination=pagination,
        products=pagination.items,
        current_cat=slug,
        sort=sort,
        nav_categories=nav_categories,
    )


@shop_bp.route("/produtos/mais-vendidos")
def top_selling():
    """Página separada para os produtos mais vendidos"""
    page = request.args.get("page", 1, type=int)
    sort = request.args.get("sort", "popular")

    query = (
        Product.query.filter(and_(Product.is_active == True, Product.stock > 0))
        .outerjoin(OrderItem, OrderItem.product_id == Product.id)
        .outerjoin(Order, Order.id == OrderItem.order_id)
        .filter(Order.status == "entregue")
        .group_by(Product.id)
        .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
    )

    pagination = query.paginate(page=page, per_page=12, error_out=False)
    nav_categories = Category.query.all()

    return render_template(
        "shop/products.html",
        pagination=pagination,
        sort="popular",
        title="Produtos Mais Vendidos",
        nav_categories=nav_categories,
    )


@shop_bp.route("/busca-avancada")
def advanced_search():
    """Busca avançada com opção de ordenação aleatória"""
    q = request.args.get("q", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    category_id = request.args.get("category_id", type=int)
    sort = request.args.get("sort", "random")  # Padrão aleatório

    query = Product.query.filter(and_(Product.is_active == True, Product.stock > 0))

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Product.name.ilike(like), Product.description.ilike(like))
        )

    if min_price:
        query = query.filter(Product.price >= min_price)

    if max_price:
        query = query.filter(Product.price <= max_price)

    if category_id:
        query = query.filter(Product.category_id == category_id)

    # Aplicar ordenação
    if sort == "random":
        query = query.order_by(func.random())
    elif sort == "price_asc":
        query = query.order_by(Product.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Product.price.desc())
    elif sort == "popular":
        query = (
            query.outerjoin(OrderItem, OrderItem.product_id == Product.id)
            .outerjoin(Order, Order.id == OrderItem.order_id)
            .filter(or_(Order.status == "entregue", Order.status == None))
            .group_by(Product.id)
            .order_by(func.coalesce(func.sum(OrderItem.quantity), 0).desc())
        )
    else:
        query = query.order_by(func.random())

    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=12, error_out=False)

    categories = Category.query.all()
    nav_categories = categories

    return render_template(
        "shop/advanced_search.html",
        pagination=pagination,
        q=q,
        min_price=min_price,
        max_price=max_price,
        category_id=category_id,
        sort=sort,
        categories=categories,
        nav_categories=nav_categories,
    )


@shop_bp.route("/pedido/<int:order_id>/solicitar-alteracao", methods=["POST"])
@login_required
def request_order_change(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    if order.user_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for("account.orders"))

    if order.status != "pendente":
        flash("Apenas pedidos pendentes podem ser alterados.", "warning")
        return redirect(url_for("account.order_detail", code=order.code))

    change_type = request.form.get("change_type")
    message = request.form.get("message")

    req = OrderRequest(
        order_id=order.id,
        user_id=current_user.id,
        request_type="alteracao",
        change_type=change_type,
        message=message,
        status="pendente",
    )
    db.session.add(req)
    db.session.commit()

    flash(
        "✅ Solicitação de alteração enviada! Em breve entraremos em contato.",
        "success",
    )
    return redirect(url_for("account.order_detail", code=order.code))


@shop_bp.route("/pedido/<int:order_id>/solicitar-cancelamento", methods=["POST"])
@login_required
def request_order_cancellation(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    if order.user_id != current_user.id:
        flash("Acesso negado.", "danger")
        return redirect(url_for("account.orders"))

    if order.status != "pendente":
        flash("Apenas pedidos pendentes podem ser cancelados.", "warning")
        return redirect(url_for("account.order_detail", code=order.code))

    reason = request.form.get("reason")
    details = request.form.get("details")

    req = OrderRequest(
        order_id=order.id,
        user_id=current_user.id,
        request_type="cancelamento",
        reason=reason,
        message=details,
        status="pendente",
    )
    db.session.add(req)
    db.session.commit()

    flash("✅ Solicitação de cancelamento enviada! Aguarde a confirmação.", "info")
    return redirect(url_for("account.order_detail", code=order.code))


# 🔥 API de busca em tempo real (Live Search)
@shop_bp.route("/api/search")
def api_search():
    """
    Retorna produtos filtrados em tempo real em formato JSON.
    Query params:
    - q: termo de busca (mínimo 1 caractere)
    - limit: máximo de resultados (padrão 8, máximo 20)
    """
    q = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", "8")), 20)

    # Validação: precisa de pelo menos 1 caractere para buscar
    if not q or len(q) < 1:
        return jsonify({"results": [], "total": 0})

    # Buscar produtos ativos que correspondem ao termo
    like = f"%{q}%"
    products = (
        Product.query.filter(
            Product.is_active == True,
            or_(Product.name.ilike(like), Product.description.ilike(like)),
        )
        .limit(limit)
        .all()
    )

    # Formatar resposta
    results = []
    for p in products:
        results.append(
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "price": float(p.price),
                "image": p.image_url or "/static/images/default.png",
                "stock": p.stock,
                "category": p.category.name if p.category else "Sem categoria",
            }
        )

    return jsonify({"results": results, "total": len(results), "query": q})

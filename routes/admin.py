from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    current_app,
    jsonify,
    abort,
)
from flask_login import login_required, current_user
from sqlalchemy import func, and_
from models import db
from models.user import User
from models.product import Product
from models.category import Category
from models.supplier import Supplier
from models.order import Order, OrderItem
from models.order_request import OrderRequest
from admin.forms import ProductForm, CategoryForm, SupplierForm, OrderUpdateForm
from utils.decorators import admin_required
from utils.helpers import slugify, save_upload
from services.ai_product_service import ai_service
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta

admin_bp = Blueprint("admin", __name__)


def _get_or_404(model, ident):
    instance = db.session.get(model, ident)
    if instance is None:
        abort(404)
    return instance


@admin_bp.before_request
@login_required
@admin_required
def _guard():
    pass


@admin_bp.route("/")
def dashboard():
    from datetime import datetime, timedelta

    # Período padrão
    period = request.args.get("period", 30, type=int)
    now = datetime.utcnow()
    days_ago = now - timedelta(days=period)
    previous_period_start = days_ago - timedelta(days=period)
    previous_period_end = days_ago

    # ========== VALORES PADRÃO (caso queries falhem) ==========
    total_sales = 0
    previous_sales = 0
    sales_delta = 0
    profit = 0
    total_orders = 0
    previous_orders = 0
    orders_delta = 0
    total_products = 0
    low_stock_count = 0
    total_customers = 0
    new_customers = 0
    sales_by_day = []
    labels = []
    status_counts = {s: 0 for s in ["pendente", "pago", "enviado", "entregue", "cancelado", "recusado"]}
    cat_labels = []
    cat_data = []
    top_products = []
    recent_orders = []
    recent_activity = []
    sparkline_data = []
    pending_orders_count = 0

    # ========== FUNÇÃO AUXILIAR PARA EXECUTAR QUERIES COM SEGURANÇA ==========
    def safe_query(query_func, default=None):
        try:
            return query_func()
        except Exception as e:
            print(f"Erro na query: {e}")
            return default

    # ========== EXECUTAR QUERIES COM TRATAMENTO ==========
    try:
        # Dados básicos que sempre devem funcionar
        total_products = safe_query(lambda: Product.query.count(), 0)
        total_customers = safe_query(lambda: User.query.filter(User.is_admin == False).count(), 0)
        
        # Se não conseguiu produtos, provavelmente tabelas não existem
        if total_products == 0:
            flash("⚠️ Nenhum produto encontrado. Verifique se as tabelas foram criadas.", "warning")
            return render_template("admin/dashboard.html", ...)  # Use valores padrão
        
        # Queries mais complexas com try/except individual
        try:
            total_sales_result = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(
                Order.status.in_(["pago", "enviado", "entregue"]),
                Order.created_at >= days_ago
            ).scalar()
            total_sales = total_sales_result or 0
        except Exception as e:
            print(f"Erro total_sales: {e}")
            total_sales = 0

        try:
            previous_sales_result = db.session.query(func.coalesce(func.sum(Order.total), 0)).filter(
                Order.status.in_(["pago", "enviado", "entregue"]),
                Order.created_at.between(previous_period_start, previous_period_end)
            ).scalar()
            previous_sales = previous_sales_result or 0
            sales_delta = ((total_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
        except Exception as e:
            print(f"Erro previous_sales: {e}")

        # TOP PRODUTOS (versão mais segura)
        try:
            top_products = db.session.query(Product, func.sum(OrderItem.quantity).label("total_sold"))\
                .join(OrderItem, OrderItem.product_id == Product.id)\
                .join(Order, Order.id == OrderItem.order_id)\
                .filter(Order.status.in_(["pago", "enviado", "entregue"]))\
                .group_by(Product.id)\
                .order_by(func.sum(OrderItem.quantity).desc())\
                .limit(5).all()
        except Exception as e:
            print(f"Erro top_products: {e}")
            top_products = []

        # PEDIDOS RECENTES
        try:
            recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()
            total_orders = Order.query.filter(Order.created_at >= days_ago).count()
        except Exception as e:
            print(f"Erro recent_orders: {e}")
            recent_orders = []
            total_orders = 0

    except Exception as e:
        print(f"Erro geral no dashboard: {e}")
        flash(f"Erro ao carregar dashboard: {str(e)}", "danger")

    # Status labels para o gráfico
    status_labels_map = {
        "pendente": "Pendente",
        "pago": "Pago",
        "enviado": "Enviado",
        "entregue": "Entregue",
        "cancelado": "Cancelado",
        "recusado": "Recusado",
    }

    return render_template(
        "admin/dashboard.html",
        total_sales=total_sales,
        sales_delta=round(sales_delta, 1),
        profit=profit,
        total_orders=total_orders,
        orders_delta=round(orders_delta, 1),
        total_products=total_products,
        low_stock_count=low_stock_count,
        total_customers=total_customers,
        new_customers=new_customers,
        sales_chart_labels=labels,
        sales_chart_data=sales_by_day,
        status_labels=[status_labels_map.get(s, s) for s in status_counts.keys()],
        status_data=list(status_counts.values()),
        cat_labels=cat_labels,
        cat_data=cat_data,
        top_products=top_products,
        recent_orders=recent_orders,
        sales_goal=50000,
        recent_activity=recent_activity,
        pending_orders_count=pending_orders_count,
        sparkline_data=sparkline_data,
    )


# Função auxiliar para formatar BRL
def format_brl(value):
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


# Gerar SKU automático para novos produtos
def generate_next_sku():
    """
    Gera o próximo SKU automaticamente no formato numérico com 4 dígitos.
    Busca o SKU do último produto cadastrado e incrementa em 1.
    Se não houver produtos ou SKU inválido, começa do 0001.
    """
    # Buscar o último produto cadastrado (pelo ID, que é auto-incremento)
    last_product = Product.query.order_by(Product.id.desc()).first()

    if last_product and last_product.sku:
        try:
            # Converte o SKU existente para inteiro (remove zeros à esquerda automaticamente)
            last_sku = int(last_product.sku)
            next_sku = last_sku + 1
            # Retorna com 4 dígitos (ex: 1 -> 0001, 47 -> 0047, 100 -> 0100)
            return f"{next_sku:04d}"
        except (ValueError, TypeError):
            # Se o SKU não for numérico, busca o maior SKU numérico
            # Isso cobre produtos antigos que podem ter SKU não numérico
            all_products = Product.query.all()
            max_sku = 0
            for product in all_products:
                try:
                    sku_num = int(product.sku)
                    if sku_num > max_sku:
                        max_sku = sku_num
                except (ValueError, TypeError):
                    continue
            next_sku = max_sku + 1 if max_sku > 0 else 1
            return f"{next_sku:04d}"
    else:
        # Se não houver produtos, começa do 0001
        return "0001"


# ---------- Products ----------
def _populate_product_choices(form):
    form.category_id.choices = [
        (c.id, c.name) for c in Category.query.order_by(Category.name).all()
    ]

    suppliers = Supplier.query.order_by(Supplier.name).all()

    form.supplier_id.choices = [(s.id, s.name) for s in suppliers]

    if not suppliers:
        form.supplier_id.choices = [(0, "Sem fornecedor")]


@admin_bp.route("/produtos/gerar-descricao", methods=["GET"])
def generate_product_description():
    product_name = request.args.get("name", "").strip()
    current_description = request.args.get("description", "").strip()

    if not product_name:
        return jsonify({"success": False, "message": "Informe o nome do produto."}), 400

    result = ai_service.generate_product_description(
        product_name, current_description=current_description
    )

    return jsonify(
        {
            "success": True,
            "description": result["description"],
            "source": result["source"],
        }
    )


@admin_bp.route("/produtos")
def products():
    items = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", items=items)


@admin_bp.route("/produtos/novo", methods=["GET", "POST"])
def product_new():
    form = ProductForm()
    _populate_product_choices(form)

    # Gerar próximo SKU automaticamente para novo produto
    if request.method == "GET":
        form.sku.data = generate_next_sku()
        # Definir valor padrão do estoque como 1
        if not form.stock.data:
            form.stock.data = 1

    if form.validate_on_submit():
        # Garantir que o SKU tenha 4 dígitos (formatação)
        sku_raw = form.sku.data.strip()
        name_raw = form.name.data.strip()

        # Verificar se SKU já existe
        existing_sku = Product.query.filter_by(sku=sku_raw).first()
        if existing_sku:
            flash(
                f"SKU '{sku_raw}' já está em uso. Por favor, use um SKU diferente.",
                "danger",
            )
            return render_template("admin/product_form.html", form=form, mode="novo")

        # Verificar se o SKU é numérico
        if not sku_raw.isdigit():
            flash("SKU deve conter apenas números.", "danger")
            return render_template("admin/product_form.html", form=form, mode="novo")

        # Converter para inteiro e depois formatar com 4 dígitos
        try:
            sku_number = int(sku_raw)
            formatted_sku = f"{sku_number:04d}"
        except ValueError:
            flash("SKU inválido.", "danger")
            return render_template("admin/product_form.html", form=form, mode="novo")

        # Verificar se o SKU formatado já existe (redundante, mas seguro)
        existing_formatted = Product.query.filter_by(sku=formatted_sku).first()
        if existing_formatted and existing_formatted.sku != sku_raw:
            flash(
                f"SKU '{formatted_sku}' já está em uso. Por favor, use um SKU diferente.",
                "danger",
            )
            return render_template("admin/product_form.html", form=form, mode="novo")

        # VERIFICAÇÃO MELHORADA: Verificar se nome já existe (case insensitive e trimmed)
        # Isso impede cadastrar "Produto Teste" e "produto teste" como diferentes
        existing_name = Product.query.filter(
            func.trim(func.lower(Product.name)) == func.trim(func.lower(name_raw))
        ).first()

        if existing_name:
            flash(
                f"Produto com nome '{form.name.data}' já existe. Não é permitido duplicar nomes de produtos.",
                "danger",
            )
            return render_template("admin/product_form.html", form=form, mode="novo")

        # Verificação adicional: Nome similar (opcional, para evitar confusão)
        # Isso encontra nomes que começam igual (ex: "Camisa Azul" e "Camisa Azul Premium")
        similar_names = Product.query.filter(
            Product.name.ilike(f"%{name_raw}%")
        ).first()

        if similar_names and len(name_raw) > 10:
            flash(
                f"Atenção: Existe um produto similar chamado '{similar_names.name}'. Deseja continuar?",
                "warning",
            )
            # Não impede o cadastro, apenas avisa (opcional)

        img = (
            save_upload(form.image_file.data, current_app.config["UPLOAD_FOLDER"])
            or form.image_url.data
        )

        # Garantir que o estoque seja 1 se não foi informado
        stock_value = form.stock.data if form.stock.data is not None else 1

        p = Product(
            sku=formatted_sku,  # Usar o SKU formatado com 4 dígitos
            name=form.name.data,
            slug=slugify(form.name.data),
            description=form.description.data,
            price=form.price.data,
            supplier_price=form.supplier_price.data or 0,
            stock=stock_value,  # Usar o valor com padrão 1
            category_id=form.category_id.data or None,
            supplier_id=form.supplier_id.data or None,
            image_url=img,
            is_active=form.is_active.data,
            is_featured=form.is_featured.data,
        )
        db.session.add(p)
        db.session.commit()
        flash(
            f"Produto '{p.name}' criado com SKU {formatted_sku} e estoque inicial de {stock_value} unidade(s).",
            "success",
        )
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html", form=form, mode="novo")


@admin_bp.route("/produtos/<int:pid>/editar", methods=["GET", "POST"])
def product_edit(pid):
    p = _get_or_404(Product, pid)
    form = ProductForm(obj=p)
    _populate_product_choices(form)

    if form.validate_on_submit():
        # Verificar se SKU já existe (excluindo o produto atual)
        sku_raw = form.sku.data.strip()
        name_raw = form.name.data.strip()

        existing_sku = Product.query.filter(
            Product.sku == sku_raw, Product.id != pid
        ).first()
        if existing_sku:
            flash(
                f"SKU '{sku_raw}' já está em uso por outro produto. Por favor, use um SKU diferente.",
                "danger",
            )
            return render_template(
                "admin/product_form.html", form=form, mode="editar", product=p
            )

        # Verificar se o SKU é numérico
        if not sku_raw.isdigit():
            flash("SKU deve conter apenas números.", "danger")
            return render_template(
                "admin/product_form.html", form=form, mode="editar", product=p
            )

        # Formatar SKU com 4 dígitos
        try:
            sku_number = int(sku_raw)
            formatted_sku = f"{sku_number:04d}"
        except ValueError:
            flash("SKU inválido.", "danger")
            return render_template(
                "admin/product_form.html", form=form, mode="editar", product=p
            )

        # VERIFICAÇÃO MELHORADA: Verificar se nome já existe (excluindo o produto atual)
        existing_name = Product.query.filter(
            func.trim(func.lower(Product.name)) == func.trim(func.lower(name_raw)),
            Product.id != pid,
        ).first()

        if existing_name:
            flash(
                f"Produto com nome '{form.name.data}' já existe em outro produto. Não é permitido duplicar nomes.",
                "danger",
            )
            return render_template(
                "admin/product_form.html", form=form, mode="editar", product=p
            )

        # ========== CORREÇÃO DA FOTO ==========
        # 1. Primeiro, verifica se tem upload de arquivo
        img = save_upload(form.image_file.data, current_app.config["UPLOAD_FOLDER"])

        # 2. Se NÃO tem upload de arquivo, usa o valor do campo image_url (link)
        if not img:
            img = form.image_url.data  # <-- ESTA LINHA ESTAVA FALTANDO!

        # 3. Se ainda assim não tem imagem, mantém a existente
        if not img:
            img = p.image_url
        # ========== FIM DA CORREÇÃO ==========

        # Atualizar campos manualmente
        p.sku = formatted_sku
        p.name = form.name.data
        p.slug = slugify(form.name.data)
        p.description = form.description.data
        p.price = form.price.data
        p.supplier_price = form.supplier_price.data or 0
        p.stock = form.stock.data or 0
        p.category_id = form.category_id.data or None
        p.supplier_id = form.supplier_id.data or None
        p.image_url = img  # Agora atualiza com o link manual ou upload
        p.is_active = form.is_active.data
        p.is_featured = form.is_featured.data

        db.session.commit()
        flash(f"Produto '{p.name}' atualizado com SKU {formatted_sku}.", "success")
        return redirect(url_for("admin.products"))

    return render_template(
        "admin/product_form.html", form=form, mode="editar", product=p
    )


@admin_bp.route("/produtos/padronizar-skus", methods=["POST"])
@login_required
def padronize_skus():
    """
    Rota para padronizar SKUs existentes para o formato de 4 dígitos.
    Ex: 1 -> 0001, 47 -> 0047, 100 -> 0100
    """
    if not current_user.is_admin:
        return jsonify({"success": False, "message": "Apenas administradores"}), 403

    try:
        products = Product.query.all()
        updated = 0

        for product in products:
            try:
                # Tenta converter o SKU atual para número
                sku_number = int(product.sku)
                formatted_sku = f"{sku_number:04d}"

                # Se o SKU já está no formato correto, pula
                if product.sku == formatted_sku:
                    continue

                # Verifica se o SKU formatado já existe
                existing = Product.query.filter_by(sku=formatted_sku).first()
                if existing and existing.id != product.id:
                    print(
                        f"Conflito: SKU {formatted_sku} já existe para produto {existing.id}"
                    )
                    continue

                # Atualiza o SKU
                old_sku = product.sku
                product.sku = formatted_sku
                updated += 1
                print(f"Atualizado: {old_sku} -> {formatted_sku}")

            except (ValueError, TypeError):
                # SKU não é numérico, pular ou tratar conforme necessidade
                print(f"SKU não numérico ignorado: {product.sku}")
                continue

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"Padronização concluída. {updated} SKUs atualizados para o formato de 4 dígitos.",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/produtos/verificar-nome", methods=["POST"])
@login_required
def check_product_name():
    """Verifica se o nome do produto já existe (validação em tempo real)"""
    data = request.get_json()
    name = data.get("name", "").strip()
    product_id = data.get("product_id")  # Para edição, ignorar o próprio produto

    if not name:
        return jsonify({"exists": False, "message": ""})

    query = Product.query.filter(
        func.trim(func.lower(Product.name)) == func.trim(func.lower(name))
    )

    if product_id:
        query = query.filter(Product.id != int(product_id))

    exists = query.first() is not None

    return jsonify(
        {
            "exists": exists,
            "message": "Nome já está em uso" if exists else "Nome disponível",
        }
    )


# Rota adicional: Buscar produtos por nome (para evitar duplicatas manualmente)
@admin_bp.route("/produtos/buscar-por-nome", methods=["GET"])
@login_required
def search_products_by_name():
    """Busca produtos por nome (útil para verificar duplicatas antes de cadastrar)"""
    query = request.args.get("q", "").strip()

    if not query or len(query) < 3:
        return jsonify({"products": []})

    products = Product.query.filter(Product.name.ilike(f"%{query}%")).limit(10).all()

    results = [
        {"id": p.id, "name": p.name, "sku": p.sku, "price": float(p.price)}
        for p in products
    ]

    return jsonify({"products": results})


@admin_bp.route("/produtos/<int:pid>/excluir", methods=["POST"])
def product_delete(pid):
    p = _get_or_404(Product, pid)
    db.session.delete(p)
    db.session.commit()
    flash("Produto excluído.", "info")
    return redirect(url_for("admin.products"))


# ---------- Categories ----------
@admin_bp.route("/categorias", methods=["GET", "POST"])
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        c = Category(name=form.name.data, slug=slugify(form.name.data))
        db.session.add(c)
        db.session.commit()
        flash("Categoria criada.", "success")
        return redirect(url_for("admin.categories"))
    return render_template(
        "admin/categories.html",
        items=Category.query.order_by(Category.name).all(),
        form=form,
    )


@admin_bp.route("/categorias/<int:cid>/excluir", methods=["POST"])
def category_delete(cid):
    c = _get_or_404(Category, cid)
    db.session.delete(c)
    db.session.commit()
    return redirect(url_for("admin.categories"))


# ---------- Suppliers ----------
@admin_bp.route("/fornecedores", methods=["GET", "POST"])
def suppliers():
    form = SupplierForm()
    if form.validate_on_submit():
        s = Supplier(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            avg_shipping_days=form.avg_shipping_days.data or 7,
            notes=form.notes.data,
        )
        db.session.add(s)
        db.session.commit()
        flash("Fornecedor criado.", "success")
        return redirect(url_for("admin.suppliers"))
    return render_template(
        "admin/suppliers.html", items=Supplier.query.all(), form=form
    )


@admin_bp.route("/fornecedores/<int:sid>/excluir", methods=["POST"])
def supplier_delete(sid):
    s = _get_or_404(Supplier, sid)
    db.session.delete(s)
    db.session.commit()
    return redirect(url_for("admin.suppliers"))


# ---------- Orders (PRINCIPAL - Rota correta) ----------
@admin_bp.route("/pedidos")
@login_required
def orders():
    """Lista de pedidos com estatísticas e paginação"""
    if not current_user.is_admin and not current_user.is_staff:
        flash("Acesso negado.", "danger")
        return redirect(url_for("admin.dashboard"))

    # Pega o status da URL (pode vir em maiúsculo ou minúsculo)
    status_param = request.args.get("status")
    status = status_param.lower() if status_param else None

    page = request.args.get("page", 1, type=int)
    per_page = 20

    query = Order.query

    # Aplica o filtro de status se existir
    if status:
        query = query.filter(Order.status == status)

    # Ordenar por data decrescente
    query = query.order_by(Order.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Estatísticas (contando todos os pedidos, sem filtro)
    stats = {
        "total": Order.query.count(),
        "pendente": Order.query.filter_by(status="pendente").count(),
        "pago": Order.query.filter_by(status="pago").count(),
        "enviado": Order.query.filter_by(status="enviado").count(),
        "entregue": Order.query.filter_by(status="entregue").count(),
        "cancelado": Order.query.filter_by(status="cancelado").count(),
        "recusado": (
            Order.query.filter_by(status="recusado").count()
            if hasattr(Order, "recusado")
            else 0
        ),
    }

    return render_template(
        "admin/orders.html",
        items=pagination.items,
        pagination=pagination,
        status=status_param,  # Mantém o original para o template
        stats=stats,
    )


@admin_bp.route("/pedidos/<int:oid>", methods=["GET", "POST"])
@login_required
def order_detail(oid):
    order = _get_or_404(Order, oid)
    form = OrderUpdateForm(obj=order)
    if form.validate_on_submit():
        order.status = form.status.data.lower() if form.status.data else order.status
        order.tracking_code = form.tracking_code.data
        order.payment_note = form.payment_note.data
        db.session.commit()
        flash("Pedido atualizado.", "success")
        return redirect(url_for("admin.order_detail", oid=order.id))
    return render_template("admin/order_detail.html", order=order, form=form)


# ---------- Users ----------
@admin_bp.route("/usuarios")
def users():
    return render_template(
        "admin/users.html", items=User.query.order_by(User.created_at.desc()).all()
    )


@admin_bp.route("/usuarios/<int:uid>/toggle", methods=["POST"])
def user_toggle(uid):
    u = _get_or_404(User, uid)
    u.is_active_flag = not u.is_active_flag
    db.session.commit()
    return redirect(url_for("admin.users"))


# ---------- ROTAS PARA EXCLUSÃO DE PEDIDOS ----------


@admin_bp.route("/pedido/<int:order_id>/deletar", methods=["POST"])
@login_required
def delete_order(order_id):
    """
    Exclui permanentemente um pedido cancelado/recusado.

    IMPORTANTE: Apenas deleta pedidos que já estão cancelados/recusados.
    O estoque já foi restaurado quando o pedido foi cancelado.
    """
    if not current_user.is_admin and not current_user.is_staff:
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    order = _get_or_404(Order, order_id)

    # Verificar se o pedido pode ser excluído (apenas cancelados ou recusados)
    if order.status not in ["cancelado", "recusado"]:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f"Não é possível excluir pedido com status '{order.status}'. Apenas pedidos cancelados ou recusados podem ser excluídos.",
                }
            ),
            400,
        )

    try:
        order_code = order.code

        # Não precisamos restaurar estoque porque já foi restaurado
        # quando o pedido foi cancelado

        # Excluir solicitações relacionadas primeiro
        OrderRequest.query.filter_by(order_id=order.id).delete()

        # Excluir itens do pedido
        OrderItem.query.filter_by(order_id=order.id).delete()

        # Excluir o pedido
        db.session.delete(order)
        db.session.commit()

        return jsonify(
            {"success": True, "message": f"Pedido {order_code} excluído com sucesso"}
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Erro ao excluir: {str(e)}"}), 500


@admin_bp.route("/pedidos/limpar-cancelados", methods=["POST"])
@login_required
def clean_cancelled_orders():
    """
    Limpa todos os pedidos cancelados e recusados (com filtro opcional de dias).

    IMPORTANTE: Apenas deleta pedidos que já estão cancelados/recusados.
    O estoque já foi restaurado quando o pedido foi cancelado.
    """
    if not current_user.is_admin and not current_user.is_staff:
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    try:
        from datetime import datetime, timedelta

        data = request.get_json()
        days = data.get("days") if data else None

        query = Order.query.filter(
            db.or_(Order.status == "cancelado", Order.status == "recusado")
        )

        if days:
            cutoff_date = datetime.utcnow() - timedelta(days=int(days))
            query = query.filter(Order.created_at <= cutoff_date)

        orders_to_delete = query.all()
        count = len(orders_to_delete)

        for order in orders_to_delete:
            # Não precisamos restaurar estoque porque já foi restaurado
            # quando o pedido foi cancelado
            OrderRequest.query.filter_by(order_id=order.id).delete()
            OrderItem.query.filter_by(order_id=order.id).delete()
            db.session.delete(order)

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"{count} pedido(s) cancelado(s)/recusado(s) foram excluídos permanentemente.",
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/pedidos/excluir-em-massa", methods=["POST"])
@login_required
def bulk_delete_orders():
    """Exclui múltiplos pedidos em massa"""
    if not current_user.is_admin and not current_user.is_staff:
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    try:
        data = request.get_json()

        # Verificar se data existe
        if not data:
            return jsonify({"success": False, "message": "Dados não enviados"}), 400

        order_ids = data.get("order_ids", [])

        if not order_ids:
            return (
                jsonify({"success": False, "message": "Nenhum pedido selecionado"}),
                400,
            )

        # Buscar os pedidos
        orders = Order.query.filter(Order.id.in_(order_ids)).all()

        if not orders:
            return (
                jsonify({"success": False, "message": "Pedidos não encontrados"}),
                404,
            )

        # Verificar status
        invalid_orders = []
        for order in orders:
            if order.status.lower() not in ["cancelado", "recusado"]:
                invalid_orders.append(f"{order.code} ({order.status})")

        if invalid_orders:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Os seguintes pedidos não podem ser excluídos: {', '.join(invalid_orders)}",
                    }
                ),
                400,
            )

        # Excluir
        count = 0
        for order in orders:
            try:
                # Excluir solicitações relacionadas
                OrderRequest.query.filter_by(order_id=order.id).delete()
                # Excluir itens do pedido
                OrderItem.query.filter_by(order_id=order.id).delete()
                # Excluir o pedido
                db.session.delete(order)
                count += 1
            except Exception as e:
                print(f"Erro ao excluir pedido {order.id}: {e}")
                continue

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": f"{count} pedido(s) excluídos permanentemente com sucesso.",
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"Erro geral: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/pedido/<int:order_id>/cancelar-e-restaurar", methods=["POST"])
@login_required
def cancel_and_restore_stock(order_id):
    """Cancela o pedido e restaura o estoque dos produtos"""
    if not current_user.is_admin and not current_user.is_staff:
        return jsonify({"success": False, "message": "Acesso negado"}), 403

    order = _get_or_404(Order, order_id)

    # Usar o método do modelo Order
    success, message, total_restored = order.cancel_and_restore_stock()

    if success:
        db.session.commit()
        return jsonify({"success": True, "message": message})
    else:
        db.session.rollback()
        return jsonify({"success": False, "message": message}), 400


@admin_bp.route("/order/<int:order_id>/cancel", methods=["POST"])
@login_required
def admin_cancel_order(order_id):
    """Cancela um pedido e restaura estoque (versão consolidada)"""
    if not current_user.is_admin:
        flash("Acesso negado.", "danger")
        return redirect(url_for("admin.dashboard"))

    order = _get_or_404(Order, order_id)

    # Usar o método do modelo Order
    success, message, _ = order.cancel_and_restore_stock()

    if success:
        db.session.commit()
        flash(f"Pedido #{order.code} {message.lower()}", "success")
    else:
        flash(f"Erro: {message}", "danger")

    return redirect(url_for("admin.order_detail", oid=order.id))


@admin_bp.route("/relatorios")
def reports():
    """Página de relatórios"""
    # Por enquanto, apenas redireciona ou mostra mensagem
    flash("Funcionalidade de relatórios em desenvolvimento.", "info")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/configuracoes")
def settings():
    """Página de configurações"""
    # Por enquanto, apenas redireciona ou mostra mensagem
    flash("Funcionalidade de configurações em desenvolvimento.", "info")
    return redirect(url_for("admin.dashboard"))

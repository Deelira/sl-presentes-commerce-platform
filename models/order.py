from datetime import datetime

from sqlalchemy import func

from . import db
from .product import Product

ORDER_STATUSES = ["pendente", "pago", "enviado", "entregue", "cancelado"]


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="pendente", nullable=False)
    total = db.Column(db.Float, nullable=False, default=0.0)

    # Dados do cliente
    customer_name = db.Column(db.String(120))
    cpf = db.Column(db.String(14), nullable=False)
    phone = db.Column(db.String(40))
    
    # Endereço
    cep = db.Column(db.String(20))
    address = db.Column(db.String(255))
    complement = db.Column(db.String(100))
    number = db.Column(db.String(10))
    city = db.Column(db.String(120))
    state = db.Column(db.String(40))

    # Rastreio / pagamento
    tracking_code = db.Column(db.String(80))
    payment_method = db.Column(db.String(30), default="PIX")
    payment_note = db.Column(db.Text)
    payment_data = db.Column(db.JSON)  # Armazena dados do Mercado Pago (QR code, etc)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan", lazy=True)

    @property
    def status_class(self):
        return {
            "pendente": "warning",
            "pago": "info",
            "enviado": "primary",
            "entregue": "success",
            "cancelado": "danger",
        }.get(self.status, "secondary")
    
    @property
    def full_address(self):
        """Retorna o endereço completo formatado"""
        address_parts = [
            self.address,
            f", {self.number}" if self.number else "",
            f" - {self.complement}" if self.complement else "",
            f"\n{self.cep} - {self.city}/{self.state}" if self.cep else ""
        ]
        return "".join(address_parts).strip()
    
    @property
    def masked_cpf(self):
        """Retorna CPF mascarado para exibição"""
        if not self.cpf or len(self.cpf) < 11:
            return self.cpf
        clean_cpf = self.cpf.replace(".", "").replace("-", "")
        return f"{clean_cpf[:3]}.***.***-{clean_cpf[-2:]}"
    
    def cancel_and_restore_stock(self):
        """Cancela o pedido e restaura o estoque dos produtos."""
        if self.status in ["enviado", "entregue"]:
            return False, f"Não é possível cancelar pedido com status '{self.status}'", 0

        if self.status not in ["pendente", "pago"]:
            return False, f"Pedido com status '{self.status}' não pode ser cancelado", 0

        restored_units = 0

        try:
            for item in self.items:
                product = db.session.get(Product, item.product_id)
                if product:
                    product.stock += item.quantity
                    restored_units += item.quantity

            self.status = "cancelado"
            return (
                True,
                f"cancelado com sucesso. {restored_units} unidade(s) restaurada(s)",
                restored_units,
            )
        except Exception as e:
            return False, f"Erro ao cancelar pedido: {str(e)}", 0
    
    # MÉTODOS CORRIGIDOS - agora na classe Order
    @classmethod
    def get_sales_total(cls):
        """Retorna total de vendas (pedidos pagos, enviados ou entregues)"""
        return db.session.query(func.coalesce(func.sum(cls.total), 0)).filter(
            cls.status.in_(["pago", "enviado", "entregue"])
        ).scalar()
    
    @classmethod
    def get_profit_total(cls):
        """Retorna lucro total"""
        return db.session.query(
            func.coalesce(func.sum((OrderItem.unit_price - OrderItem.supplier_price) * OrderItem.quantity), 0)
        ).join(OrderItem, OrderItem.order_id == cls.id)\
         .filter(cls.status.in_(["pago", "enviado", "entregue"]))\
         .scalar()
    
    @classmethod
    def get_status_counts(cls):
        """Retorna contagem de pedidos por status"""
        counts = db.session.query(
            cls.status, func.count(cls.id)
        ).group_by(cls.status).all()
        
        result = {
            'total': cls.query.count(),
            'pendente': 0,
            'pago': 0,
            'enviado': 0,
            'entregue': 0,
            'cancelado': 0
        }
        
        for status, count in counts:
            if status in result:
                result[status] = count
        
        return result


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    product_name = db.Column(db.String(180))
    sku = db.Column(db.String(40))
    unit_price = db.Column(db.Float, nullable=False)
    supplier_price = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    product = db.relationship("Product")

    @property
    def subtotal(self):
        return self.unit_price * self.quantity
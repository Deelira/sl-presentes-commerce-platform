from datetime import datetime
from . import db


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)              # venda
    supplier_price = db.Column(db.Float, default=0.0)        # custo
    stock = db.Column(db.Integer, default=1)                # virtual
    image_url = db.Column(db.String(300))                    # main image
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def margin(self):
        if not self.supplier_price:
            return self.price
        return self.price - self.supplier_price

    @property
    def margin_pct(self):
        if not self.price:
            return 0
        return (self.margin / self.price) * 100

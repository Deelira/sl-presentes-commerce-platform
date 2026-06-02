from datetime import datetime
from models import db  # mudar de . import db para models import db

class OrderRequest(db.Model):
    __tablename__ = "order_requests"
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    request_type = db.Column(db.String(20))
    change_type = db.Column(db.String(50))
    reason = db.Column(db.String(100))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default="pendente")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    order = db.relationship("Order", backref="requests", foreign_keys=[order_id])
    user = db.relationship("User", backref="order_requests", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<OrderRequest {self.id} - {self.request_type}>"
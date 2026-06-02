from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Importar todos os modelos DEPOIS de definir db
from .user import User
from .product import Product
from .category import Category
from .order import Order, OrderItem
from .order_request import OrderRequest
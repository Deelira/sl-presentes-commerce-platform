"""Inicializa banco SQLite com dados de exemplo e credenciais explícitas."""

import os

from app import create_app
from config import is_placeholder
from models import db
from models.category import Category
from models.product import Product
from models.supplier import Supplier
from models.user import User
from utils.helpers import slugify


def _get_init_credentials():
    admin_email = os.getenv("INIT_ADMIN_EMAIL")
    admin_password = os.getenv("INIT_ADMIN_PASSWORD")

    if not admin_email or is_placeholder(admin_email):
        raise SystemExit(
            "Defina INIT_ADMIN_EMAIL no .env antes de executar python init_db.py"
        )

    if not admin_password or is_placeholder(admin_password):
        raise SystemExit(
            "Defina INIT_ADMIN_PASSWORD no .env antes de executar python init_db.py"
        )

    demo_enabled = os.getenv("INIT_DEMO_ENABLED", "false").lower() == "true"
    demo_email = os.getenv("INIT_DEMO_EMAIL")
    demo_password = os.getenv("INIT_DEMO_PASSWORD")

    if demo_enabled and (
        not demo_email or is_placeholder(demo_email)
    ):
        raise SystemExit(
            "INIT_DEMO_ENABLED está ativo, mas INIT_DEMO_EMAIL não foi configurado."
        )

    if demo_enabled and (
        not demo_password or is_placeholder(demo_password)
    ):
        raise SystemExit(
            "INIT_DEMO_ENABLED está ativo, mas INIT_DEMO_PASSWORD não foi configurado."
        )

    return admin_email, admin_password, demo_email, demo_password


app = create_app()

with app.app_context():
    if os.getenv("INIT_RESET_DB", "false").lower() == "true":
        db.drop_all()

    db.create_all()

    admin_email, admin_password, demo_email, demo_password = _get_init_credentials()

    admin = User(name="Administrador", email=admin_email, role="admin")
    admin.set_password(admin_password)

    users_to_add = [admin]

    if demo_email and demo_password:
        cliente = User(name="Cliente Demo", email=demo_email, phone="(11) 99999-0000")
        cliente.set_password(demo_password)
        users_to_add.append(cliente)

    db.session.add_all(users_to_add)

    cats_data = ["Eletrônicos", "Acessórios", "Casa & Smart", "Áudio", "Gamer"]
    cats = []
    for n in cats_data:
        c = Category(name=n, slug=slugify(n))
        db.session.add(c)
        cats.append(c)

    sups_data = [
        ("Tech Brasil Distribuidora", "(11) 4002-8922", "vendas@techbr.com", 5),
        ("MegaImport SP", "(11) 3333-4444", "comercial@megaimport.com", 7),
    ]
    sups = []
    for n, ph, em, days in sups_data:
        s = Supplier(name=n, phone=ph, email=em, avg_shipping_days=days)
        db.session.add(s)
        sups.append(s)

    db.session.flush()

    products = [
        (
            "FONE-001",
            "Fone Bluetooth NeonPro X5",
            "Fone sem fio com cancelamento de ruído ativo, 30h de bateria e som Hi-Fi.",
            299.90,
            149.00,
            cats[3],
            sups[0],
            True,
        ),
        (
            "MOUSE-002",
            "Mouse Gamer RGB UltraLight",
            "Mouse leve com 16000 DPI, sensor óptico de alta precisão e iluminação RGB.",
            189.00,
            79.00,
            cats[4],
            sups[0],
            True,
        ),
        (
            "WATCH-003",
            "Smartwatch FitNeon S2",
            "Monitor cardíaco, GPS integrado, mais de 60 modos esportivos e bateria de 14 dias.",
            449.00,
            220.00,
            cats[0],
            sups[1],
            True,
        ),
        (
            "CHARGE-004",
            "Carregador Wireless 25W",
            "Carregamento por indução rápido para smartphones compatíveis.",
            129.90,
            49.00,
            cats[1],
            sups[0],
            False,
        ),
        (
            "CAM-005",
            "Câmera de Segurança Wi-Fi 2K",
            "Visão noturna, áudio bidirecional, detecção de movimento e acesso pelo app.",
            219.00,
            110.00,
            cats[2],
            sups[1],
            True,
        ),
        (
            "LAMP-006",
            "Lâmpada Smart RGB Wi-Fi",
            "16 milhões de cores, controle por app e assistentes de voz.",
            79.90,
            25.00,
            cats[2],
            sups[1],
            False,
        ),
        (
            "KB-007",
            "Teclado Mecânico RGB 60%",
            "Switches mecânicos hot-swap, layout compacto e iluminação por tecla.",
            389.00,
            199.00,
            cats[4],
            sups[0],
            True,
        ),
        (
            "HUB-008",
            "Hub USB-C 7 em 1",
            "HDMI 4K, USB 3.0, leitor SD/microSD e PD 100W.",
            199.00,
            89.00,
            cats[1],
            sups[1],
            False,
        ),
    ]
    for sku, name, desc, price, cost, cat, sup, feat in products:
        db.session.add(
            Product(
                sku=sku,
                name=name,
                slug=slugify(name),
                description=desc,
                price=price,
                supplier_price=cost,
                category_id=cat.id,
                supplier_id=sup.id,
                is_active=True,
                is_featured=feat,
                image_url=f"https://picsum.photos/seed/{sku}/600/600",
            )
        )

    db.session.commit()
    print("✓ Banco inicializado")
    print(f"  Admin:   {admin_email}")
    if demo_email:
        print(f"  Cliente: {demo_email}")

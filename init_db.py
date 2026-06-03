"""Inicializa banco SQLite com dados de exemplo e credenciais explícitas."""

import os
from pathlib import Path

# Garantir que o diretório instance existe
BASE_DIR = Path(__file__).parent.resolve()
INSTANCE_DIR = Path(__file__).parent / 'instance'
INSTANCE_DIR.mkdir(exist_ok=True)

# Configurar banco de dados
os.environ.setdefault('DATABASE_URL', f'sqlite:///{INSTANCE_DIR / "sl-presentes.db"}')

# Verificar permissões
print(f"✅ Diretório instance: {INSTANCE_DIR}")
print(f"✅ Pode escrever: {os.access(INSTANCE_DIR, os.W_OK)}")

from app import create_app
from config import is_placeholder
from models import db
from models.category import Category
from models.product import Product
from models.supplier import Supplier
from models.user import User
from utils.helpers import slugify


def _get_init_credentials():
    admin_email = os.getenv("INIT_ADMIN_EMAIL", "admin@teste.com")
    admin_password = os.getenv("INIT_ADMIN_PASSWORD", "admin123")

    if not admin_email or is_placeholder(admin_email):
        raise SystemExit(
            "Defina INIT_ADMIN_EMAIL no .env antes de executar python init_db.py"
        )

    if not admin_password or is_placeholder(admin_password):
        raise SystemExit(
            "Defina INIT_ADMIN_PASSWORD no .env antes de executar python init_db.py"
        )

    demo_enabled = os.getenv("INIT_DEMO_ENABLED", "true").lower() == "true"
    demo_email = os.getenv("INIT_DEMO_EMAIL", "cliente@exemplo.com")
    demo_password = os.getenv("INIT_DEMO_PASSWORD", "cliente123")

    if demo_enabled and (not demo_email or is_placeholder(demo_email)):
        demo_email = "cliente@exemplo.com"

    if demo_enabled and (not demo_password or is_placeholder(demo_password)):
        demo_password = "cliente123"

    return admin_email, admin_password, demo_email, demo_password


app = create_app()

with app.app_context():
    # Resetar banco se solicitado
    if os.getenv("INIT_RESET_DB", "false").lower() == "true":
        print("⚠️  Resetando banco de dados...")
        db.drop_all()
        print("✅ Banco resetado")

    # Criar tabelas se não existirem
    db.create_all()
    print("✅ Tabelas verificadas/criadas")

    admin_email, admin_password, demo_email, demo_password = _get_init_credentials()

    # Verificar se admin já existe
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(name="Administrador", email=admin_email, role="admin")
        admin.set_password(admin_password)
        db.session.add(admin)
        print(f"✅ Administrador criado: {admin_email}")
    else:
        print(f"ℹ️  Administrador já existe: {admin_email}")

    # Verificar se cliente demo já existe
    if demo_email and demo_password:
        cliente = User.query.filter_by(email=demo_email).first()
        if not cliente:
            cliente = User(name="Cliente Demo", email=demo_email, phone="(11) 99999-0000")
            cliente.set_password(demo_password)
            db.session.add(cliente)
            print(f"✅ Cliente demo criado: {demo_email}")
        else:
            print(f"ℹ️  Cliente demo já existe: {demo_email}")

    # Verificar se categorias já existem
    if Category.query.count() == 0:
        cats_data = ["Eletrônicos", "Acessórios", "Casa & Smart", "Áudio", "Gamer"]
        cats = []
        for n in cats_data:
            c = Category(name=n, slug=slugify(n))
            db.session.add(c)
            cats.append(c)
        print(f"✅ {len(cats_data)} categorias criadas")
    else:
        print(f"ℹ️  Categorias já existem ({Category.query.count()} encontradas)")
        cats = Category.query.all()

    # Verificar se fornecedores já existem
    if Supplier.query.count() == 0:
        sups_data = [
            ("Tech Brasil Distribuidora", "(11) 4002-8922", "vendas@techbr.com", 5),
            ("MegaImport SP", "(11) 3333-4444", "comercial@megaimport.com", 7),
        ]
        sups = []
        for n, ph, em, days in sups_data:
            s = Supplier(name=n, phone=ph, email=em, avg_shipping_days=days)
            db.session.add(s)
            sups.append(s)
        print(f"✅ {len(sups_data)} fornecedores criados")
    else:
        print(f"ℹ️  Fornecedores já existem ({Supplier.query.count()} encontrados)")
        sups = Supplier.query.all()

    db.session.flush()

    # Verificar se produtos já existem
    if Product.query.count() == 0:
        # Mapear categorias por nome
        cat_map = {c.name: c for c in cats}
        sup_map = {s.name: s for s in sups}
        
        products = [
            (
                "FONE-001",
                "Fone Bluetooth NeonPro X5",
                "Fone sem fio com cancelamento de ruído ativo, 30h de bateria e som Hi-Fi.",
                299.90,
                149.00,
                "Áudio",
                "Tech Brasil Distribuidora",
                True,
            ),
            (
                "MOUSE-002",
                "Mouse Gamer RGB UltraLight",
                "Mouse leve com 16000 DPI, sensor óptico de alta precisão e iluminação RGB.",
                189.00,
                79.00,
                "Gamer",
                "Tech Brasil Distribuidora",
                True,
            ),
            (
                "WATCH-003",
                "Smartwatch FitNeon S2",
                "Monitor cardíaco, GPS integrado, mais de 60 modos esportivos e bateria de 14 dias.",
                449.00,
                220.00,
                "Eletrônicos",
                "MegaImport SP",
                True,
            ),
            (
                "CHARGE-004",
                "Carregador Wireless 25W",
                "Carregamento por indução rápido para smartphones compatíveis.",
                129.90,
                49.00,
                "Acessórios",
                "Tech Brasil Distribuidora",
                False,
            ),
            (
                "CAM-005",
                "Câmera de Segurança Wi-Fi 2K",
                "Visão noturna, áudio bidirecional, detecção de movimento e acesso pelo app.",
                219.00,
                110.00,
                "Casa & Smart",
                "MegaImport SP",
                True,
            ),
            (
                "LAMP-006",
                "Lâmpada Smart RGB Wi-Fi",
                "16 milhões de cores, controle por app e assistentes de voz.",
                79.90,
                25.00,
                "Casa & Smart",
                "MegaImport SP",
                False,
            ),
            (
                "KB-007",
                "Teclado Mecânico RGB 60%",
                "Switches mecânicos hot-swap, layout compacto e iluminação por tecla.",
                389.00,
                199.00,
                "Gamer",
                "Tech Brasil Distribuidora",
                True,
            ),
            (
                "HUB-008",
                "Hub USB-C 7 em 1",
                "HDMI 4K, USB 3.0, leitor SD/microSD e PD 100W.",
                199.00,
                89.00,
                "Acessórios",
                "MegaImport SP",
                False,
            ),
        ]
        
        for sku, name, desc, price, cost, cat_name, sup_name, feat in products:
            cat = cat_map.get(cat_name)
            sup = sup_map.get(sup_name)
            if cat and sup:
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
                        stock=100,  # Adicionando estoque padrão
                    )
                )
        print(f"✅ {len(products)} produtos criados")
    else:
        print(f"ℹ️  Produtos já existem ({Product.query.count()} encontrados)")

    # Commit final
    db.session.commit()
    print("\n🎉 Banco de dados inicializado com sucesso!")
    print(f"  Admin:   {admin_email}")
    if demo_email:
        print(f"  Cliente: {demo_email}")
    print("\n💡 Para resetar o banco na próxima vez, use:")
    print("  INIT_RESET_DB=true python init_db.py")
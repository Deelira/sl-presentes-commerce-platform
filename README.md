# Sl Presentes — Sistema de Vendas Sem Estoque (Dropshipping Nacional)

Sistema completo em **Flask + SQLAlchemy + SQLite**, com loja virtual, painel admin,
checkout PIX manual, gestão de pedidos, fornecedores e usuários.

## Stack
- Python 3.10+
- Flask 3, Flask-Login, Flask-WTF, Flask-SQLAlchemy
- Jinja2, Bootstrap 5 (CDN), CSS/JS puros
- SQLite (trocável para Postgres alterando `DATABASE_URL`)

## Instalação

```bash
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows
pip install -r requirements.txt
python init_db.py                 # cria banco + dados de exemplo + admin
python app.py                     # http://127.0.0.1:5000
```

## Configuração inicial
1. Copie `.env.example` para `.env`.
2. Defina `INIT_ADMIN_EMAIL`, `INIT_ADMIN_PASSWORD` e, se quiser, `INIT_DEMO_EMAIL` e `INIT_DEMO_PASSWORD`.
3. Para recriar o banco com seed seguro, ajuste `INIT_RESET_DB=true` e execute `python init_db.py`.

## Deploy em VPS (gunicorn + nginx)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

Configure nginx como reverse-proxy para `127.0.0.1:8000` e sirva `/static`
diretamente para melhor performance.

## Estrutura

```
project/
├── app.py                  # factory + blueprint registration
├── config.py
├── init_db.py              # seed + admin
├── requirements.txt
├── models/                 # SQLAlchemy models
├── routes/                 # Blueprints (shop, auth, cart, checkout, admin, account)
├── services/               # regras de negócio
├── auth/                   # forms + decorators
├── admin/                  # forms admin
├── utils/                  # helpers
├── templates/              # Jinja2
├── static/                 # css, js, images
└── instance/app.db         # SQLite
```

## Roadmap (preparado, não implementado)
- Mercado Pago API (substituir `services/payment.py`)
- Rastreamento automático Correios
- Cupons, afiliados, chatbot
- API REST (`/api/v1/...`) com tokens

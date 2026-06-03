# SL Presentes — Sistema de E-commerce Completo

Sistema completo em **Flask + SQLAlchemy + PostgreSQL/SQLite**, com loja virtual, painel administrativo, checkout PIX e cartão, gestão de pedidos, produtos, categorias, fornecedores e usuários.

## Funcionalidades

### 🛍️ Loja Virtual
- Catálogo de produtos com categorias
- Busca por produtos (com autocomplete)
- Carrinho de compras (gratuito, sem login)
- Checkout com cálculo de frete (opcional)
- Pagamentos via PIX (manual) e Mercado Pago
- Histórico de pedidos do cliente

### 👑 Painel Administrativo
- Gestão completa de produtos (CRUD)
- Upload de imagens para produtos
- Controle de estoque (entrada/saída manual)
- Gestão de categorias e fornecedores
- Gerenciamento de pedidos (status: pendente, pago, enviado, entregue, cancelado)
- Dashboard com métricas (vendas, lucro, produtos mais vendidos)
- Gestão de usuários clientes
- Pedidos recentes e atividade do sistema

### 👤 Área do Cliente
- Login/registro com validação
- Perfil do usuário
- Histórico completo de pedidos
- Acompanhamento de status do pedido
- Recuperação de senha (email)

## Stack Tecnológico

- **Backend**: Python 3.10+, Flask 3
- **Banco de Dados**: PostgreSQL (produção) / SQLite (desenvolvimento)
- **ORM**: SQLAlchemy 2.0, Flask-Migrate
- **Autenticação**: Flask-Login
- **Formulários**: Flask-WTF
- **Frontend**: Jinja2, Bootstrap 5, CSS/JS personalizado
- **Integrações**: Mercado Pago API, OpenAI (descrições automáticas)
- **Servidor**: Gunicorn + Nginx (produção)

## Instalação Local

### 1. Clone o repositório

bash  
git clone https://github.com/Deelira/sl-presentes-commerce-platform.git  
cd sl-presentes-commerce-platform  

### 2. Crie o ambiente virtual
python -m venv venv  
source venv/bin/activate          # Linux/Mac  
# venv\Scripts\activate           # Windows  

### 3. Instale dependências
pip install -r requirements.txt  

### 4. Configure variáveis de ambiente
cp .env.example .env  

# Edite .env com suas configurações

SECRET_KEY=sua-chave-secreta-aqui  
DATABASE_URL=sqlite:///instance/app.db  # ou postgresql://...  
INIT_ADMIN_EMAIL=admin@exemplo.com  
INIT_ADMIN_PASSWORD=admin123  

### 5. Inicialize o banco de dados
# Cria tabelas e usuários padrão
python init_db.py  

### 6. Execute o sistema
python app.py  

Contas de teste (criadas automaticamente)  
Tipo	Email	Senha  
Admin	admin@exemplo.com	admin123  
Cliente	cliente@exemplo.com	cliente123  


# Recriar banco com dados de exemplo
python init_db.py  

# Criar migrações do banco
flask db init  
flask db migrate -m "mensagem"  
flask db upgrade  

# Rodar em modo debug
python app.py  

# Produção com Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"  

# Testar conexão com banco
python -c "from app import create_app; app=create_app(); print('OK')"

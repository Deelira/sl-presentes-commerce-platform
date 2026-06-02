from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, BooleanField, SelectField, FileField
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class ProductForm(FlaskForm):
    sku = StringField("SKU", validators=[DataRequired(), Length(max=40)])
    name = StringField("Nome", validators=[DataRequired(), Length(max=180)])
    description = TextAreaField("Descrição")
    price = FloatField("Preço de venda", validators=[DataRequired(), NumberRange(min=0)])
    supplier_price = FloatField("Preço do fornecedor", validators=[Optional(), NumberRange(min=0)])
    stock = IntegerField("Estoque virtual", default=1, validators=[Optional(), NumberRange(min=0)])
    category_id = SelectField(
        "Categoria",
        coerce=int,
        validators=[Optional()],
        validate_choice=False
    )
    supplier_id = SelectField(
        "Fornecedor",
        coerce=int,
        validators=[Optional()],
        validate_choice=False
    )
    image_url = StringField("URL da imagem (ou envie abaixo)")
    image_file = FileField("Imagem (upload)")
    is_active = BooleanField("Ativo", default=True)
    is_featured = BooleanField("Destaque")


class CategoryForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired(), Length(max=80)])


class SupplierForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired(), Length(max=120)])
    phone = StringField("Telefone")
    email = StringField("Email")
    avg_shipping_days = IntegerField("Prazo médio (dias)", default=7)
    notes = TextAreaField("Observações")


class OrderUpdateForm(FlaskForm):
    status = SelectField("Status", choices=[
        ("pendente", "Pendente"), ("pago", "Pago"),
        ("enviado", "Enviado"), ("entregue", "Entregue"),
        ("cancelado", "Cancelado"),
    ])
    tracking_code = StringField("Código de rastreio")
    payment_note = TextAreaField("Observações de pagamento")


class CheckoutForm(FlaskForm):
    customer_name = StringField("Nome completo", validators=[DataRequired(), Length(max=120)])
    cpf = StringField("CPF", validators=[DataRequired(), Length(min=11, max=14)])
    phone = StringField("Telefone", validators=[DataRequired(), Length(max=30)])
    cep = StringField("CEP", validators=[DataRequired(), Length(min=8, max=9)])
    address = StringField("Endereço", validators=[DataRequired(), Length(max=255)])
    complement = StringField("Complemento", validators=[Optional(), Length(max=100)])
    number = StringField("Número", validators=[DataRequired(), Length(max=10)])
    city = StringField("Cidade", validators=[DataRequired(), Length(max=120)])
    state = StringField("Estado", validators=[DataRequired(), Length(min=2, max=2)])
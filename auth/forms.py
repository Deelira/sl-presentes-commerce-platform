from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    Optional,
    ValidationError,
)
import re


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Senha", validators=[DataRequired()])
    remember = BooleanField("Lembrar de mim")


class RegisterForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Telefone", validators=[Length(max=30)])
    cpf = StringField(
        "CPF",
        validators=[
            DataRequired(message="CPF é obrigatório"),
            Length(min=11, max=14, message="CPF deve ter entre 11 e 14 caracteres"),
        ],
    )
    password = PasswordField("Senha", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField(
        "Confirmar senha", validators=[DataRequired(), EqualTo("password")]
    )

    def validate_cpf(self, field):
        """Valida se o CPF é válido e único"""
        cpf = self.limpar_cpf(field.data)

        if len(cpf) != 11:
            raise ValidationError("CPF deve conter 11 dígitos")

        if cpf == cpf[0] * 11:
            raise ValidationError("CPF inválido")

        if not self.validar_cpf_algoritmo(cpf):
            raise ValidationError("CPF inválido")

    def limpar_cpf(self, cpf):
        """Remove pontos, traços e espaços do CPF"""
        if not cpf:
            return ""
        return re.sub(r"[^0-9]", "", str(cpf))

    def validar_cpf_algoritmo(self, cpf):
        """Valida o algoritmo do CPF"""
        soma = 0
        for i in range(9):
            soma += int(cpf[i]) * (10 - i)
        resto = 11 - (soma % 11)
        if resto >= 10:
            resto = 0
        if resto != int(cpf[9]):
            return False

        soma = 0
        for i in range(10):
            soma += int(cpf[i]) * (11 - i)
        resto = 11 - (soma % 11)
        if resto >= 10:
            resto = 0
        if resto != int(cpf[10]):
            return False

        return True


class ForgotForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])


class VerifyCPFForm(FlaskForm):
    cpf = StringField("CPF", validators=[DataRequired(), Length(min=11, max=14)])


class ResetForm(FlaskForm):
    password = PasswordField("Nova senha", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField(
        "Confirmar", validators=[DataRequired(), EqualTo("password")]
    )


class CheckoutForm(FlaskForm):
    customer_name = StringField(
        "Nome completo", validators=[DataRequired(), Length(max=120)]
    )
    cpf = StringField("CPF", validators=[DataRequired(), Length(min=11, max=14)])
    phone = StringField("Telefone", validators=[DataRequired(), Length(max=30)])
    cep = StringField("CEP", validators=[DataRequired(), Length(min=8, max=9)])
    address = StringField("Endereço", validators=[DataRequired(), Length(max=255)])
    complement = StringField("Complemento", validators=[Optional(), Length(max=100)])
    number = StringField("Número", validators=[DataRequired(), Length(max=10)])
    city = StringField("Cidade", validators=[DataRequired(), Length(max=120)])
    state = StringField("Estado", validators=[DataRequired(), Length(min=2, max=2)])


class ProfileForm(FlaskForm):
    name = StringField("Nome", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Telefone", validators=[Optional(), Length(max=30)])
    cpf = StringField("CPF", validators=[Optional(), Length(min=11, max=14)])


class PasswordForm(FlaskForm):
    current_password = PasswordField("Senha atual", validators=[DataRequired()])
    new_password = PasswordField(
        "Nova senha", validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Confirmar nova senha",
        validators=[DataRequired(), EqualTo("new_password")],
    )

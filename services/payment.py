"""Integração com Mercado Pago para pagamentos PIX."""

import io
import logging
from datetime import datetime

import qrcode
from flask import current_app

try:
    import mercadopago
except ImportError:
    mercadopago = None

logger = logging.getLogger(__name__)


def _get_mp_client():
    """Retorna cliente inicializado do Mercado Pago."""
    if not mercadopago:
        raise ImportError("Mercado Pago SDK não está instalado. Execute: pip install mercadopago")
    
    token = current_app.config.get("MP_ACCESS_TOKEN")
    if not token:
        raise ValueError("MP_ACCESS_TOKEN não configurado no .env")
    
    return mercadopago.SDK(token)


def create_pix_charge(order):
    """
    Cria uma cobrança PIX dinâmica via Mercado Pago.
    Retorna dados de pagamento com QR code e instruções.
    """
    try:
        sdk = _get_mp_client()
        
        payment_data = {
            "transaction_amount": float(order.total),
            "description": f"Pedido {order.code}",
            "payment_method_id": "pix",
            "payer": {
                "email": order.user.email if order.user else order.cpf,
                "first_name": order.customer_name,
            },
            "notification_url": current_app.config.get("MERCADO_PAGO_NOTIFICATION_URL", ""),
        }
        
        payment = sdk.payment().create(payment_data)
        payment_response = payment.get("response", {})
        
        if payment_response.get("status") in ["pending", "processing"]:
            qr_data = payment_response.get("point_of_interaction", {}).get("transaction_data", {})
            
            return {
                "method": "PIX",
                "success": True,
                "amount": order.total,
                "order_code": order.code,
                "payment_id": payment_response.get("id"),
                "qr_code": qr_data.get("qr_code", ""),
                "qr_code_url": qr_data.get("qr_code_url", ""),
                "copy_paste_code": qr_data.get("qr_code", ""),
                "status": payment_response.get("status"),
                "expires_at": payment_response.get("date_of_expiration", ""),
                "instructions": (
                    f"Escaneie o QR code ao lado ou copie o código PIX abaixo. "
                    f"O pagamento será confirmado automaticamente."
                ),
            }
        else:
            logger.error(f"Erro ao criar pagamento PIX: {payment_response}")
            return {
                "method": "PIX",
                "success": False,
                "error": payment_response.get("message", "Erro ao criar pagamento"),
            }
    
    except Exception as e:
        logger.error(f"Exceção ao criar pagamento PIX: {str(e)}")
        return {
            "method": "PIX",
            "success": False,
            "error": f"Erro ao processar pagamento: {str(e)}",
            "fallback": True,  # Flag para usar fallback manual
        }


def create_pix_qrcode_image(qr_string):
    """
    Gera uma imagem PNG do QR code a partir da string PIX.
    Retorna bytes da imagem para servir via HTTP.
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = io.BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)
        
        return img_io.getvalue()
    except Exception as e:
        logger.error(f"Erro ao gerar QR code: {str(e)}")
        return None


def verify_payment_status(payment_id):
    """
    Verifica o status de um pagamento no Mercado Pago.
    """
    try:
        sdk = _get_mp_client()
        payment = sdk.payment().get(payment_id)
        return payment.get("response", {})
    except Exception as e:
        logger.error(f"Erro ao verificar status do pagamento {payment_id}: {str(e)}")
        return None

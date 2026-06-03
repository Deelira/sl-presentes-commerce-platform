"""Extensões Flask para evitar importações circulares."""
from flask_wtf.csrf import CSRFProtect

# Inicializar CSRF
csrf = CSRFProtect()
"""
Autenticação simples para FisioMED.
Usa cookie com token HMAC-SHA256 assinado.
"""
import hashlib
import hmac
import os
import time
import json
import base64

# =============================================
# CONFIGURAÇÃO DE USUÁRIOS
# =============================================
# Senha armazenada como SHA-256 hash
# Para gerar novo hash: hashlib.sha256("suaSenha".encode()).hexdigest()
USERS = {
    "eduardo": {
        "password_hash": hashlib.sha256("1234567890".encode()).hexdigest(),
        "nome": "Dr. Eduardo Soares de Carvalho"
    }
}

# Chave secreta para assinar tokens (gerada aleatoriamente se não definida)
SECRET_KEY = os.environ.get("FISIOMED_SECRET", "fisiomed-secret-key-2026-change-me")
TOKEN_EXPIRY = 86400 * 7  # 7 dias

COOKIE_NAME = "fisiomed_token"


def verify_password(username: str, password: str) -> bool:
    """Verifica se usuário e senha estão corretos."""
    user = USERS.get(username.lower())
    if not user:
        return False
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(password_hash, user["password_hash"])


def create_token(username: str) -> str:
    """Cria token assinado com HMAC-SHA256."""
    payload = {
        "sub": username,
        "exp": int(time.time()) + TOKEN_EXPIRY,
        "iat": int(time.time())
    }
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_token(token: str) -> str | None:
    """Verifica token e retorna username ou None se inválido."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("sub")
    except Exception:
        return None

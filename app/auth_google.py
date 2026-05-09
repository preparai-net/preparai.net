"""
Autenticação Google OAuth + Allowlist com permissões POR FERRAMENTA + Cookie de sessão.

Schema da allowlist.json:
{
  "admins": ["email@x.com"],         # admins têm acesso a TODAS as ferramentas
  "users": [
    {"email": "x@y.com", "tools": ["fisiomed", "plataformaoqm", "separador"]}
  ]
}

Migração automática: formato antigo `"users": ["a@b.com"]` é convertido na primeira leitura.
"""
import os
import json
import time
import secrets
import urllib.request
import urllib.parse
from typing import Optional, List
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SESSION_COOKIE = "preparai_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 dias

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
SESSION_SECRET = os.environ.get("SESSION_SECRET", "").strip()

if not SESSION_SECRET:
    SESSION_SECRET = secrets.token_hex(32)
    print("[auth_google] AVISO: SESSION_SECRET não definido no env. Gerado temporariamente.")

_serializer = URLSafeTimedSerializer(SESSION_SECRET, salt="preparai-session")
ALLOWLIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "allowlist.json")

# ---------------- Ferramentas e mapeamento de paths ----------------
TOOLS = ["clinica", "questoes", "separador"]

TOOL_LABELS = {
    "clinica": "Clínica",
    "questoes": "Edição Final de Questões",
    "separador": "Separador de PDF",
}

# Aliases para retrocompatibilidade (allowlist antiga / migração)
TOOL_ALIASES = {
    "fisiomed": "clinica",            # rename: /fisiomed → /clinica
    "plataformaoqm": "questoes",      # rename antigo
    "oqm": "questoes",
}

# Ordem importa: prefixos mais específicos primeiro.
PATH_TO_TOOL = [
    ("/api/questoes", "questoes"),
    ("/api/oqm", "questoes"),
    ("/api/separador", "separador"),
    ("/api/gerar", "clinica"),
    ("/clinica/gerar", "clinica"),
    ("/fisiomed/gerar", "clinica"),
    ("/questoes", "questoes"),
    ("/plataformaoqm", "questoes"),
    ("/separador", "separador"),
    ("/clinica", "clinica"),
    ("/fisiomed", "clinica"),
]


def path_to_tool(path: str) -> Optional[str]:
    for prefix, tool in PATH_TO_TOOL:
        if path.startswith(prefix):
            return tool
    return None


# ---------------- Allowlist ----------------
def _default_allowlist():
    return {"admins": ["dudssoares@gmail.com"], "users": []}


def _migrate(data: dict) -> dict:
    """
    Converte formato antigo para novo:
    - users como lista de strings → lista de dicts {email, tools}
    - tools com nomes antigos (plataformaoqm, oqm) → nomes novos (questoes)
    """
    changed = False
    if "admins" not in data:
        data["admins"] = []
    if "users" not in data:
        data["users"] = []
    new_users = []
    for u in data["users"]:
        if isinstance(u, str):
            new_users.append({"email": u, "tools": list(TOOLS)})
            changed = True
        elif isinstance(u, dict):
            tools = u.get("tools")
            if not isinstance(tools, list):
                tools = list(TOOLS)
                changed = True
            # Aplica aliases (plataformaoqm → questoes)
            mapped = []
            for t in tools:
                new_t = TOOL_ALIASES.get(t, t)
                if new_t != t:
                    changed = True
                if new_t in TOOLS:
                    mapped.append(new_t)
            # Dedupe preservando ordem
            seen = set()
            mapped = [t for t in mapped if not (t in seen or seen.add(t))]
            new_users.append({"email": u.get("email", "").lower().strip(), "tools": mapped})
    data["users"] = new_users
    return data if not changed else (save_allowlist(data) or data)


def load_allowlist() -> dict:
    try:
        with open(ALLOWLIST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = _default_allowlist()
        save_allowlist(data)
        return data
    return _migrate(data)


def save_allowlist(data: dict):
    with open(ALLOWLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _norm_email(email: str) -> str:
    return (email or "").lower().strip()


def is_admin(email: str) -> bool:
    if not email:
        return False
    data = load_allowlist()
    return _norm_email(email) in [_norm_email(e) for e in data.get("admins", [])]


def get_user_tools(email: str) -> List[str]:
    """Retorna lista de tools que o email pode acessar. Admin = todas."""
    if not email:
        return []
    e = _norm_email(email)
    data = load_allowlist()
    if e in [_norm_email(x) for x in data.get("admins", [])]:
        return list(TOOLS)
    for u in data.get("users", []):
        if _norm_email(u.get("email", "")) == e:
            return [t for t in u.get("tools", []) if t in TOOLS]
    return []


def can_access_tool(email: str, tool: str) -> bool:
    if not email or not tool:
        return False
    return tool in get_user_tools(email)


def is_allowed(email: str) -> bool:
    """Tem acesso a pelo menos uma ferramenta."""
    return bool(get_user_tools(email))


# ---------------- Google token verification ----------------
def verify_google_access_token(access_token: str) -> Optional[dict]:
    if not access_token:
        return None
    try:
        url = "https://www.googleapis.com/oauth2/v3/tokeninfo?" + urllib.parse.urlencode(
            {"access_token": access_token}
        )
        with urllib.request.urlopen(url, timeout=10) as resp:
            info = json.loads(resp.read().decode("utf-8"))

        if GOOGLE_CLIENT_ID and info.get("aud") != GOOGLE_CLIENT_ID:
            return None
        if not info.get("email_verified") in (True, "true"):
            return None

        try:
            req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                ui = json.loads(resp.read().decode("utf-8"))
        except Exception:
            ui = {}

        return {
            "email": info.get("email", "").lower(),
            "name": ui.get("name") or info.get("email", ""),
            "picture": ui.get("picture", ""),
        }
    except Exception as e:
        print(f"[auth_google] erro verificando token: {e}")
        return None


# ---------------- Sessão ----------------
def create_session_cookie(email: str, name: str = "", picture: str = "") -> str:
    payload = {"email": email.lower(), "name": name, "picture": picture, "iat": int(time.time())}
    return _serializer.dumps(payload)


def verify_session_cookie(cookie_value: str) -> Optional[dict]:
    if not cookie_value:
        return None
    try:
        return _serializer.loads(cookie_value, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    except Exception:
        return None


def get_user_from_request(request) -> Optional[dict]:
    """
    Retorna dict do usuário SE estiver autenticado E tiver pelo menos uma ferramenta liberada.
    Não checa permissão por path — isso é responsabilidade do middleware/handler.
    """
    cookie = request.cookies.get(SESSION_COOKIE)
    user = verify_session_cookie(cookie)
    if not user:
        return None
    if not is_allowed(user.get("email", "")):
        return None
    return user

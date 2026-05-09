"""
/admin — gerenciamento da allowlist com PERMISSÕES POR FERRAMENTA.
Acesso restrito a admins.
"""
import re
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.auth_google import (
    get_user_from_request,
    is_admin,
    load_allowlist,
    save_allowlist,
    TOOLS,
    TOOL_LABELS,
)

router = APIRouter(prefix="/api/admin", tags=["Admin"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _require_admin(request: Request):
    user = get_user_from_request(request)
    if not user or not is_admin(user.get("email", "")):
        return None
    return user


def _norm(e: str) -> str:
    return (e or "").lower().strip()


@router.get("/allowlist")
async def get_list(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "acesso negado"}, status_code=403)
    data = load_allowlist()
    return {
        "admins": data.get("admins", []),
        "users": data.get("users", []),
        "tools": [{"key": k, "label": TOOL_LABELS.get(k, k)} for k in TOOLS],
    }


@router.post("/allowlist/add")
async def add_email(request: Request):
    if not _require_admin(request):
        return JSONResponse({"error": "acesso negado"}, status_code=403)
    body = await request.json()
    email = _norm(body.get("email", ""))
    role = (body.get("role") or "user").strip().lower()  # "admin" | "user"
    tools = body.get("tools") or []

    if not EMAIL_RE.match(email):
        return JSONResponse({"error": "email inválido"}, status_code=400)
    if role not in ("admin", "user"):
        return JSONResponse({"error": "role deve ser 'admin' ou 'user'"}, status_code=400)
    if not isinstance(tools, list):
        return JSONResponse({"error": "tools deve ser lista"}, status_code=400)
    tools = [t for t in tools if t in TOOLS]
    if role == "user" and not tools:
        return JSONResponse({"error": "selecione ao menos uma ferramenta para o usuário"}, status_code=400)

    data = load_allowlist()
    data["admins"] = [e for e in data.get("admins", []) if _norm(e) != email]
    data["users"] = [u for u in data.get("users", []) if _norm(u.get("email", "")) != email]

    if role == "admin":
        data["admins"].append(email)
    else:
        data["users"].append({"email": email, "tools": tools})

    save_allowlist(data)
    return {"ok": True, "allowlist": load_allowlist()}


@router.post("/allowlist/update")
async def update_user_tools(request: Request):
    """Atualiza apenas as tools de um usuário existente (não-admin)."""
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "acesso negado"}, status_code=403)
    body = await request.json()
    email = _norm(body.get("email", ""))
    tools = body.get("tools") or []
    if not email:
        return JSONResponse({"error": "email vazio"}, status_code=400)
    tools = [t for t in tools if t in TOOLS]

    data = load_allowlist()
    found = False
    for u in data.get("users", []):
        if _norm(u.get("email", "")) == email:
            u["tools"] = tools
            found = True
            break
    if not found:
        return JSONResponse({"error": "usuário não encontrado (admins não têm tools individuais — possuem todas)"}, status_code=404)
    save_allowlist(data)
    return {"ok": True, "allowlist": load_allowlist()}


@router.post("/allowlist/remove")
async def remove_email(request: Request):
    user = _require_admin(request)
    if not user:
        return JSONResponse({"error": "acesso negado"}, status_code=403)
    body = await request.json()
    email = _norm(body.get("email", ""))
    if not email:
        return JSONResponse({"error": "email vazio"}, status_code=400)
    if email == _norm(user["email"]):
        return JSONResponse({"error": "Você não pode remover seu próprio acesso"}, status_code=400)

    data = load_allowlist()
    before = len(data.get("admins", [])) + len(data.get("users", []))
    data["admins"] = [e for e in data.get("admins", []) if _norm(e) != email]
    data["users"] = [u for u in data.get("users", []) if _norm(u.get("email", "")) != email]
    after = len(data["admins"]) + len(data["users"])
    if before == after:
        return JSONResponse({"error": "email não encontrado"}, status_code=404)
    save_allowlist(data)
    return {"ok": True, "allowlist": load_allowlist()}

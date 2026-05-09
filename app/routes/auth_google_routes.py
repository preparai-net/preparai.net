"""
Rotas de autenticação Google: /auth/google (POST), /auth/logout, /auth/me, /auth/config
"""
import os
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

from app.auth_google import (
    GOOGLE_CLIENT_ID,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    verify_google_access_token,
    create_session_cookie,
    is_allowed,
    is_admin,
    get_user_from_request,
    get_user_tools,
    TOOL_LABELS,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/config")
async def auth_config():
    return {"google_client_id": GOOGLE_CLIENT_ID}


@router.post("/google")
async def google_login(request: Request):
    body = await request.json()
    token = (body.get("token") or body.get("access_token") or "").strip()
    user = verify_google_access_token(token)
    if not user:
        return JSONResponse({"error": "Token inválido"}, status_code=401)

    email = user["email"]
    if not is_allowed(email):
        return JSONResponse(
            {"error": f"Acesso não autorizado para {email}. Solicite ao administrador."},
            status_code=403,
        )

    cookie = create_session_cookie(email, user.get("name", ""), user.get("picture", ""))
    response = JSONResponse(
        {
            "ok": True,
            "user": {
                "email": email,
                "name": user.get("name", ""),
                "picture": user.get("picture", ""),
                "is_admin": is_admin(email),
                "tools": get_user_tools(email),
            },
        }
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=cookie,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("ENV", "").lower() == "production",
        path="/",
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me")
async def me(request: Request):
    user = get_user_from_request(request)
    if not user:
        return JSONResponse({"error": "não autenticado"}, status_code=401)
    email = user.get("email", "")
    tools = get_user_tools(email)
    return {
        "email": email,
        "name": user.get("name", ""),
        "picture": user.get("picture", ""),
        "is_admin": is_admin(email),
        "tools": tools,
        "tool_labels": {t: TOOL_LABELS.get(t, t) for t in tools},
    }

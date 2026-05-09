"""
PreparAI / ESC — Deploy (Render/Railway)

Auth: TODAS as 3 ferramentas usam Google OAuth + allowlist por ferramenta.
- /clinica               → Google + permissão "clinica" (alias /fisiomed redireciona)
- /plataformaoqm         → Google + permissão "plataformaoqm"
- /separador             → Google + permissão "separador"
- /admin                 → Google + role admin
- O auth antigo username/password segue disponível em /auth/login-old (fallback)
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.routes.gerar import router as gerar_router
from app.routes.plataformaoqm import router as oqm_router
from app.routes.separador import router as separador_router
from app.routes.admin import router as admin_router
from app.routes.auth_google_routes import router as auth_google_router
from app.auth_google import (
    get_user_from_request, is_admin, can_access_tool, path_to_tool, TOOL_LABELS,
)

# Auth antigo continua importado para o endpoint legado
try:
    from app.auth import verify_password, create_token, COOKIE_NAME
    OLD_AUTH_AVAILABLE = True
except Exception:
    OLD_AUTH_AVAILABLE = False


app = FastAPI(title="PreparAI / ESC")


PUBLIC_PATHS = {"/", "/login", "/login.html"}
PUBLIC_PREFIXES = ("/auth/", "/static_separador/", "/static_landing/", "/clinica/assets/", "/fisiomed/assets/")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Redirects de compatibilidade ANTES de qualquer checagem
        if path == "/plataformaoqm" or path.startswith("/plataformaoqm/"):
            return RedirectResponse(url="/questoes" + path[len("/plataformaoqm"):], status_code=301)
        if path.startswith("/api/oqm/"):
            return RedirectResponse(url="/api/questoes/" + path[len("/api/oqm/"):], status_code=308)
        if path == "/fisiomed" or path.startswith("/fisiomed/"):
            return RedirectResponse(url="/clinica" + path[len("/fisiomed"):], status_code=301)

        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        if path.startswith("/clinica/assets/") or path.startswith("/fisiomed/assets/"):
            return await call_next(request)

        # /admin → Google + admin
        if path.startswith("/admin") or path.startswith("/api/admin"):
            user = get_user_from_request(request)
            if not user:
                if path.startswith("/api/"):
                    return JSONResponse({"error": "não autenticado"}, status_code=401)
                return RedirectResponse(url=f"/login?next={path}", status_code=302)
            if not is_admin(user.get("email", "")):
                if path.startswith("/api/"):
                    return JSONResponse({"error": "acesso restrito a administradores"}, status_code=403)
                return RedirectResponse(url="/", status_code=302)
            response = await call_next(request)
            return response

        # Identifica a ferramenta pelo path
        tool = path_to_tool(path)
        if tool is None:
            return await call_next(request)

        user = get_user_from_request(request)
        if not user:
            if path.startswith("/api/"):
                return JSONResponse({"error": "não autenticado"}, status_code=401)
            return RedirectResponse(url=f"/login?next={path}", status_code=302)

        if not can_access_tool(user.get("email", ""), tool):
            if path.startswith("/api/"):
                return JSONResponse(
                    {"error": f"sem permissão para a ferramenta '{TOOL_LABELS.get(tool, tool)}'"},
                    status_code=403,
                )
            return RedirectResponse(url=f"/?denied={tool}", status_code=302)

        response = await call_next(request)
        if path.startswith("/clinica") and not path.startswith("/clinica/assets/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        return response


app.add_middleware(AuthMiddleware)
app.include_router(gerar_router)
app.include_router(oqm_router)
app.include_router(separador_router)
app.include_router(admin_router)
app.include_router(auth_google_router)


# Auth antigo (username/password) — preservado como fallback caso necessário
if OLD_AUTH_AVAILABLE:
    @app.post("/auth/login-old")
    async def login_old(request: Request):
        body = await request.json()
        username = body.get("username", "")
        password = body.get("password", "")
        if not verify_password(username, password):
            return JSONResponse({"error": "Credenciais inválidas"}, status_code=401)
        token = create_token(username)
        response = JSONResponse({"ok": True})
        response.set_cookie(
            key=COOKIE_NAME, value=token, httponly=True, samesite="lax",
            max_age=86400 * 7, path="/",
        )
        return response


SEP_DIR = os.path.join(os.path.dirname(__file__), "static_separador")
LANDING_DIR = os.path.join(os.path.dirname(__file__), "static_landing")


@app.get("/login")
async def login_page():
    return FileResponse(os.path.join(SEP_DIR, "login.html"))


@app.get("/separador")
async def separador_page():
    return FileResponse(os.path.join(SEP_DIR, "index.html"))


@app.get("/admin")
async def admin_page():
    return FileResponse(os.path.join(SEP_DIR, "admin.html"))


# Estáticos
assets_dir = os.path.join(os.path.dirname(__file__), "assets")
if os.path.isdir(assets_dir):
    app.mount("/clinica/assets", StaticFiles(directory=assets_dir), name="assets")

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/clinica", StaticFiles(directory=static_dir, html=True), name="static_clinica")

questoes_static_dir = os.path.join(os.path.dirname(__file__), "static_oqm")  # diretório interno
if os.path.isdir(questoes_static_dir):
    app.mount("/questoes", StaticFiles(directory=questoes_static_dir, html=True), name="static_questoes")

if os.path.isdir(SEP_DIR):
    app.mount("/static_separador", StaticFiles(directory=SEP_DIR), name="static_separador")

if os.path.isdir(LANDING_DIR):
    app.mount("/static_landing", StaticFiles(directory=LANDING_DIR), name="static_landing")


@app.get("/")
async def root():
    if os.path.isfile(os.path.join(LANDING_DIR, "index.html")):
        return FileResponse(os.path.join(LANDING_DIR, "index.html"))
    return RedirectResponse(url="/login")

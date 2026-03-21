from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.routes.gerar import router as gerar_router
from app.auth import verify_password, create_token, verify_token, COOKIE_NAME
import os

app = FastAPI(title="FisioMED - Gerador de Documentos")

# ========================================
# MIDDLEWARE DE AUTENTICAÇÃO
# ========================================
class AuthMiddleware(BaseHTTPMiddleware):
    """Protege rotas /fisiomed exigindo login."""

    # Rotas que NÃO precisam de autenticação
    PUBLIC_PATHS = {"/", "/auth/login", "/login"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Rotas públicas
        if path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Assets do login (logo) — permitir sem auth
        if path.startswith("/fisiomed/assets/"):
            return await call_next(request)

        # Página de login estática
        if path == "/login" or path == "/login.html":
            return await call_next(request)

        # Rotas protegidas: /fisiomed e /fisiomed/*
        if path.startswith("/fisiomed"):
            token = request.cookies.get(COOKIE_NAME)
            if not token or not verify_token(token):
                # Redirecionar para login
                return RedirectResponse(url="/login", status_code=302)

        response = await call_next(request)

        # Evitar cache de arquivos estáticos (JS/CSS/HTML)
        if path.startswith("/fisiomed") and not path.startswith("/fisiomed/assets/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response

app.add_middleware(AuthMiddleware)
app.include_router(gerar_router)

# ========================================
# ROTAS DE AUTENTICAÇÃO
# ========================================
@app.post("/auth/login")
async def login(request: Request):
    """Recebe username/password, retorna cookie de sessão."""
    body = await request.json()
    username = body.get("username", "")
    password = body.get("password", "")

    if not verify_password(username, password):
        return JSONResponse({"error": "Credenciais inválidas"}, status_code=401)

    token = create_token(username)
    response = JSONResponse({"ok": True})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,  # 7 dias
        path="/"
    )
    return response


@app.get("/auth/logout")
async def logout():
    """Remove cookie e redireciona para login."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return response


# ========================================
# PÁGINA DE LOGIN
# ========================================
login_html = os.path.join(os.path.dirname(__file__), "static", "login.html")

@app.get("/login")
async def login_page():
    return FileResponse(login_html)

# ========================================
# SERVIR ARQUIVOS ESTÁTICOS
# ========================================
# Assets (imagens do logo/rodape para o frontend)
assets_dir = os.path.join(os.path.dirname(__file__), "assets")
app.mount("/fisiomed/assets", StaticFiles(directory=assets_dir), name="assets")

# Frontend (protegido pelo middleware)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/fisiomed", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/fisiomed")

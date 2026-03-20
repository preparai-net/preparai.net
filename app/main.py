from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from app.routes.gerar import router as gerar_router
import os

app = FastAPI(title="FisioMED - Gerador de Documentos")

app.include_router(gerar_router)

# Servir assets (imagens do logo/rodape para o frontend)
assets_dir = os.path.join(os.path.dirname(__file__), "assets")
app.mount("/fisiomed/assets", StaticFiles(directory=assets_dir), name="assets")

# Servir frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/fisiomed", StaticFiles(directory=static_dir, html=True), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/fisiomed")

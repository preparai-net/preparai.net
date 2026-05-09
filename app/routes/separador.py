"""
/separador — Fragmentador de PDF por capítulos.

Dois modos:
1. preview  — analisa PDF, devolve lista de capítulos detectados (bookmarks ou regex)
2. split    — gera ZIP com 1 PDF por capítulo, nome customizável

Detecção de capítulos:
- bookmarks (rápido, preciso quando PDF tem outline)
- regex     (fallback: detecta padrões "CHAPTER N", "Chapter N", "N Title" no início de páginas)
"""
import io
import os
import re
import json
import zipfile
import tempfile
import unicodedata
from typing import List, Optional
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse

import pypdf

from app.auth_google import get_user_from_request

router = APIRouter(prefix="/api/separador", tags=["Separador"])

# Limite que o backend aceita processar. Acima disso o frontend processa localmente.
# Configurável via env var (default 100MB — adequado para livros médios de até ~1000 páginas).
MAX_BACKEND_BYTES = int(os.environ.get("SEPARADOR_MAX_BACKEND_MB", "100")) * 1024 * 1024


# ============================================================
# DETECÇÃO DE CAPÍTULOS
# ============================================================
def detect_chapters_from_bookmarks(reader: pypdf.PdfReader) -> List[dict]:
    """Lê o outline do PDF e extrai capítulos (top-level numerados)."""
    chapters = []

    def walk(outline, depth=0):
        for item in outline:
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                title = (item.title or "").strip()
                m = re.match(r"^(\d+)\s+(.+)$", title)
                if m and depth <= 2:
                    try:
                        page = reader.get_destination_page_number(item) + 1
                        chapters.append({
                            "num": int(m.group(1)),
                            "title": m.group(2).strip(),
                            "start": page,
                        })
                    except Exception:
                        pass

    if reader.outline:
        walk(reader.outline)

    chapters.sort(key=lambda c: c["start"])
    seen_nums = set()
    deduped = []
    for c in chapters:
        if c["num"] in seen_nums:
            continue
        seen_nums.add(c["num"])
        deduped.append(c)

    total = len(reader.pages)
    for i, c in enumerate(deduped):
        c["end"] = (deduped[i + 1]["start"] - 1) if i + 1 < len(deduped) else total
    return deduped


def detect_chapters_from_text(reader: pypdf.PdfReader) -> List[dict]:
    """Fallback: varre texto das primeiras 200 palavras de cada página procurando padrão de capítulo."""
    total = len(reader.pages)
    found = []  # (page_1indexed, num, title)

    patterns = [
        re.compile(r"^\s*CHAPTER\s+(\d+)\s*[\.\-:]?\s*(.+)$", re.IGNORECASE),
        re.compile(r"^\s*Capítulo\s+(\d+)\s*[\.\-:]?\s*(.+)$", re.IGNORECASE),
        re.compile(r"^\s*(\d+)\s+([A-Z][A-Za-z][^\n]{2,80})$"),
    ]

    last_num = 0
    for idx in range(total):
        try:
            text = reader.pages[idx].extract_text() or ""
        except Exception:
            continue
        head_lines = [ln.strip() for ln in text.split("\n") if ln.strip()][:6]
        for ln in head_lines:
            for pat in patterns:
                m = pat.match(ln)
                if m:
                    try:
                        num = int(m.group(1))
                    except Exception:
                        continue
                    if num != last_num + 1:
                        continue
                    title = m.group(2).strip().rstrip(".,:").strip()
                    if 2 <= len(title) <= 200:
                        found.append({"num": num, "title": title, "start": idx + 1})
                        last_num = num
                        break
            else:
                continue
            break

    for i, c in enumerate(found):
        c["end"] = (found[i + 1]["start"] - 1) if i + 1 < len(found) else total
    return found


def detect_chapters(reader: pypdf.PdfReader, method: str = "auto") -> dict:
    """
    method: "bookmarks" | "regex" | "auto"
    """
    chapters_bk = []
    chapters_rx = []
    used = method
    if method in ("bookmarks", "auto"):
        chapters_bk = detect_chapters_from_bookmarks(reader)
        if method == "auto" and chapters_bk and len(chapters_bk) >= 2:
            return {"method": "bookmarks", "chapters": chapters_bk}
    if method in ("regex", "auto"):
        chapters_rx = detect_chapters_from_text(reader)
        if chapters_rx:
            return {"method": "regex", "chapters": chapters_rx}

    if chapters_bk:
        return {"method": "bookmarks", "chapters": chapters_bk}
    return {"method": used, "chapters": []}


# ============================================================
# NOMENCLATURA DOS ARQUIVOS GERADOS
# ============================================================
_INVALID_CHARS = re.compile(r"[/\\:?\*\"<>|]")


def sanitize_chapter_name(name: str, max_len: int = 80) -> str:
    s = name.replace("*", "")
    s = _INVALID_CHARS.sub("", s)
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", "_", s.strip())
    s = re.sub(r"_+", "_", s)
    if len(s) > max_len:
        cut = s[:max_len]
        if "_" in cut:
            cut = cut.rsplit("_", 1)[0]
        s = cut.rstrip("_")
    return s


def build_filename(prefix: str, num: int, title: str, start: int, end: int, max_title: int = 80) -> str:
    safe_prefix = sanitize_chapter_name(prefix or "Livro", 40)
    safe_title = sanitize_chapter_name(title, max_title)
    return f"{safe_prefix}_cap{num}_{safe_title}_pag{start}-{end}.pdf"


# ============================================================
# ENDPOINTS
# ============================================================
def _require_user(request: Request):
    return get_user_from_request(request)


@router.get("/limits")
async def limits():
    return {"max_backend_bytes": MAX_BACKEND_BYTES}


@router.post("/preview")
async def preview(
    request: Request,
    file: UploadFile = File(...),
    method: str = Form("auto"),
):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "não autenticado"}, status_code=401)

    data = await file.read()
    if len(data) > MAX_BACKEND_BYTES:
        return JSONResponse(
            {"error": f"Arquivo maior que {MAX_BACKEND_BYTES // (1024*1024)}MB. Use processamento no navegador."},
            status_code=413,
        )

    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        result = detect_chapters(reader, method=method)
        return {
            "ok": True,
            "total_pages": len(reader.pages),
            "method": result["method"],
            "chapters": result["chapters"],
        }
    except Exception as e:
        return JSONResponse({"error": f"Erro ao analisar PDF: {e}"}, status_code=500)


@router.post("/split")
async def split(
    request: Request,
    file: UploadFile = File(...),
    prefix: str = Form("Livro"),
    chapters_json: str = Form(...),
    max_title_len: int = Form(80),
):
    user = _require_user(request)
    if not user:
        return JSONResponse({"error": "não autenticado"}, status_code=401)

    data = await file.read()
    if len(data) > MAX_BACKEND_BYTES:
        return JSONResponse(
            {"error": f"Arquivo maior que {MAX_BACKEND_BYTES // (1024*1024)}MB. Use processamento no navegador."},
            status_code=413,
        )

    try:
        chapters = json.loads(chapters_json)
        if not isinstance(chapters, list) or not chapters:
            return JSONResponse({"error": "Lista de capítulos vazia"}, status_code=400)
    except Exception:
        return JSONResponse({"error": "chapters_json inválido"}, status_code=400)

    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        total = len(reader.pages)

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for ch in chapters:
                num = int(ch.get("num", 0))
                title = str(ch.get("title", ""))
                start = max(1, int(ch.get("start", 1)))
                end = min(total, int(ch.get("end", start)))
                if end < start:
                    continue
                fname = build_filename(prefix, num, title, start, end, max_title=max_title_len)

                writer = pypdf.PdfWriter()
                for p in range(start - 1, end):
                    writer.add_page(reader.pages[p])
                buf = io.BytesIO()
                writer.write(buf)
                zf.writestr(fname, buf.getvalue())

        zip_buf.seek(0)
        zip_name = f"{sanitize_chapter_name(prefix or 'Livro', 40)}_capitulos.zip"
        return StreamingResponse(
            zip_buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
        )
    except Exception as e:
        return JSONResponse({"error": f"Erro ao processar: {e}"}, status_code=500)

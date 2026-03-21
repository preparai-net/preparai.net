"""
Endpoint POST /fisiomed/gerar — Orquestrador principal.
Recebe JSON → gera .docx → converte PDF → merge → retorna PDF.
"""
import os
import json
import shutil
import tempfile
import subprocess
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from app.generators.apac import gerar_apac
from app.generators.receita_especial import gerar_receita_especial
from app.utils.soffice_convert import convert_to_pdf
from app.utils.pdf_merge import merge_pdfs

router = APIRouter()

# Diretório base dos geradores Node.js
GENERATORS_DIR = os.path.join(os.path.dirname(__file__), '..', 'generators')
# node_modules no root do projeto (/app no Docker)
NODE_MODULES = os.path.join(os.path.dirname(__file__), '..', '..', 'node_modules')


def run_node_generator(script_name: str, json_data: dict, output_path: str):
    """Executa um gerador Node.js e retorna o caminho do .docx gerado."""
    # Criar arquivo JSON temporário para passar dados
    json_path = output_path + '.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False)

    script_path = os.path.join(GENERATORS_DIR, script_name)

    env = os.environ.copy()
    env['NODE_PATH'] = NODE_MODULES

    result = subprocess.run(
        ['node', script_path, json_path, output_path],
        capture_output=True, text=True, timeout=30, env=env
    )

    # Limpar JSON temporário
    if os.path.exists(json_path):
        os.remove(json_path)

    if result.returncode != 0:
        raise RuntimeError(f"Erro no gerador {script_name}: {result.stderr}")

    return output_path


@router.post("/fisiomed/gerar")
async def gerar_documentos(request: Request):
    try:
        dados = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"erro": "JSON inválido"})

    nome = dados.get("nome_paciente", "PACIENTE").strip().upper()
    data = dados.get("data", "")
    diag1 = dados.get("diagnostico1", "")
    cid1 = dados.get("cid1", "")
    regiao = dados.get("regiao", "").strip().upper()
    apacs = dados.get("apacs", {})
    receita_simples = dados.get("receita_simples", [])
    receita_especial = dados.get("receita_especial", [])
    atestado = dados.get("atestado", {})
    laudo = dados.get("laudo", {})

    # Helper: resolver região de APAC (fallback para região principal)
    def resolve_regiao(apac_regiao):
        r = (apac_regiao or "").strip().upper()
        if not r or r == "[REGIÃO]" or r == "[REGIAO]":
            return regiao
        return r

    # Helper: sanitizar justificativa — substituir [REGIÃO] pelo valor real
    def sanitizar_justificativa(just_text):
        """Se a justificativa contém [REGIÃO], substitui pela região real."""
        if not just_text:
            return ""
        just_text = just_text.replace("[REGIÃO]", regiao).replace("[REGIAO]", regiao)
        return just_text.strip()

    # Helper: justificativa padrão para cada tipo de APAC
    def default_justificativa(tipo, reg):
        base = f"Paciente em acompanhamento com ortopedista, com quadro de dor e limitação funcional em {reg} em seguimento diagnóstico-terapêutico."
        if tipo == "retorno":
            return base
        elif tipo == "fisioterapia":
            return base
        elif tipo in ("rmn", "usg", "tc"):
            return base + " Necessitando de investigação complementar."
        elif tipo == "radiografia":
            return base + " Solicitada radiografia para investigação complementar."
        elif tipo == "consulta":
            return base
        else:
            return base

    # Criar diretório temporário
    temp_dir = tempfile.mkdtemp(prefix='fisiomed_')
    pdf_list = []

    try:
        counter = [0]

        def next_path(prefix):
            counter[0] += 1
            return os.path.join(temp_dir, f'{counter[0]:02d}_{prefix}')

        # ========================================
        # 1. APAC DE RETORNO (sempre gerada)
        # ========================================
        retorno_just = sanitizar_justificativa(
            (apacs.get("retorno", {}).get("justificativa", "") or "").strip()
        )
        if not retorno_just:
            retorno_just = default_justificativa("retorno", regiao)

        docx_path = next_path("APAC_RETORNO") + ".docx"
        gerar_apac(
            output_path=docx_path,
            nome_paciente=nome,
            data=data,
            diagnostico=diag1,
            cid=cid1,
            regiao=regiao,
            procedimento="RETORNO ORTOPEDIA",
            justificativa=retorno_just,
            quantidade="01",
            temp_dir=temp_dir
        )
        pdf_path = convert_to_pdf(docx_path, temp_dir)
        pdf_list.append(pdf_path)

        # ========================================
        # 2. APACs ADICIONAIS
        # ========================================
        apac_configs = [
            ("fisioterapia", lambda a: {
                "procedimento": f"FISIOTERAPIA MOTORA DE {resolve_regiao(a.get('regiao', ''))}",
                "regiao": resolve_regiao(a.get("regiao", "")),
                "quantidade": "20",
                "incidencia_rx": "",
            }),
            ("rmn", lambda a: {
                "procedimento": f"RMN {a.get('contraste', 'SEM CONTRASTE')} DE {resolve_regiao(a.get('regiao', ''))}",
                "regiao": resolve_regiao(a.get("regiao", "")),
                "quantidade": "01",
                "incidencia_rx": "",
            }),
            ("radiografia", lambda a: {
                "procedimento": f"RX DE {resolve_regiao(a.get('regiao', ''))}          {a.get('incidencia', 'AP E PERFIL')}",
                "regiao": resolve_regiao(a.get("regiao", "")),
                "quantidade": "01",
                "incidencia_rx": a.get("incidencia", "AP E PERFIL"),
            }),
            ("usg", lambda a: {
                "procedimento": f"USG DE {resolve_regiao(a.get('regiao', ''))}",
                "regiao": resolve_regiao(a.get("regiao", "")),
                "quantidade": "01",
                "incidencia_rx": "",
            }),
            ("tc", lambda a: {
                "procedimento": f"TC {a.get('contraste', 'SEM CONTRASTE')} DE {resolve_regiao(a.get('regiao', ''))}",
                "regiao": resolve_regiao(a.get("regiao", "")),
                "quantidade": "01",
                "incidencia_rx": "",
            }),
            ("consulta", lambda a: {
                "procedimento": f"CONSULTA - {a.get('especialidade', '')}",
                "regiao": regiao,
                "quantidade": "01",
                "incidencia_rx": "",
            }),
            ("outra", lambda a: {
                "procedimento": a.get("procedimento", ""),
                "regiao": regiao,
                "quantidade": "01",
                "incidencia_rx": "",
            }),
        ]

        for apac_type, config_fn in apac_configs:
            apac_data = apacs.get(apac_type, {})
            if apac_data.get("ativo"):
                cfg = config_fn(apac_data)
                # Justificativa: sanitizar [REGIÃO], usar fornecida ou gerar padrão
                just = sanitizar_justificativa(
                    (apac_data.get("justificativa", "") or "").strip()
                )
                if not just:
                    just = default_justificativa(apac_type, cfg["regiao"])

                docx_path = next_path(f"APAC_{apac_type.upper()}") + ".docx"
                gerar_apac(
                    output_path=docx_path,
                    nome_paciente=nome,
                    data=data,
                    diagnostico=diag1,
                    cid=cid1,
                    regiao=cfg["regiao"],
                    procedimento=cfg["procedimento"],
                    justificativa=just,
                    quantidade=cfg["quantidade"],
                    incidencia_rx=cfg.get("incidencia_rx", ""),
                    temp_dir=temp_dir
                )
                pdf_path = convert_to_pdf(docx_path, temp_dir)
                pdf_list.append(pdf_path)

        # ========================================
        # 3. RECEITA SIMPLES
        # ========================================
        if receita_simples:
            # Separar IM (DUOFLAM) dos orais
            meds_im = [m for m in receita_simples if m.get("tipo") == "im"]
            meds_oral = [m for m in receita_simples if m.get("tipo") != "im"]

            # Receita IM separada (DUOFLAM)
            if meds_im:
                docx_path = next_path("RECEITA_SIMPLES_IM") + ".docx"
                run_node_generator("receita_simples.js", {
                    "nome_paciente": nome,
                    "data": data,
                    "tipo_uso": "USO INTRAMUSCULAR",
                    "medicamentos": [{"nome": m["nome"], "posologia": m["posologia"], "quantidade": m["quantidade"]} for m in meds_im]
                }, docx_path)
                pdf_path = convert_to_pdf(docx_path, temp_dir)
                pdf_list.append(pdf_path)

            # Receita oral
            if meds_oral:
                docx_path = next_path("RECEITA_SIMPLES_ORAL") + ".docx"
                run_node_generator("receita_simples.js", {
                    "nome_paciente": nome,
                    "data": data,
                    "tipo_uso": "USO ORAL",
                    "medicamentos": [{"nome": m["nome"], "posologia": m["posologia"], "quantidade": m["quantidade"]} for m in meds_oral]
                }, docx_path)
                pdf_path = convert_to_pdf(docx_path, temp_dir)
                pdf_list.append(pdf_path)

        # ========================================
        # 4. RECEITA ESPECIAL
        # ========================================
        if receita_especial:
            # Agrupar em pares (máx 2 por receita)
            for i in range(0, len(receita_especial), 2):
                med1 = receita_especial[i]
                med2 = receita_especial[i + 1] if i + 1 < len(receita_especial) else None

                docx_path = next_path(f"RECEITA_ESPECIAL_{i // 2 + 1}") + ".docx"
                gerar_receita_especial(
                    output_path=docx_path,
                    nome_paciente=nome,
                    data=data,
                    medicamento1_nome=med1["nome"],
                    medicamento1_posologia=med1["posologia"],
                    medicamento1_qtd=med1["quantidade"],
                    medicamento2_nome=med2["nome"] if med2 else "",
                    medicamento2_posologia=med2["posologia"] if med2 else "",
                    medicamento2_qtd=med2["quantidade"] if med2 else "",
                    temp_dir=temp_dir
                )
                pdf_path = convert_to_pdf(docx_path, temp_dir)
                pdf_list.append(pdf_path)

        # ========================================
        # 5. ATESTADO
        # ========================================
        if atestado.get("ativo"):
            docx_path = next_path("ATESTADO") + ".docx"
            run_node_generator("atestado.js", {
                "nome_paciente": nome,
                "data": data,
                "dias": atestado.get("dias", 1),
                "cid": cid1,
                "diagnostico": diag1
            }, docx_path)
            pdf_path = convert_to_pdf(docx_path, temp_dir)
            pdf_list.append(pdf_path)

        # ========================================
        # 6. LAUDO
        # ========================================
        if laudo.get("ativo") and laudo.get("texto"):
            docx_path = next_path("LAUDO") + ".docx"
            run_node_generator("laudo.js", {
                "nome_paciente": nome,
                "data": data,
                "texto_laudo": laudo["texto"]
            }, docx_path)
            pdf_path = convert_to_pdf(docx_path, temp_dir)
            pdf_list.append(pdf_path)

        # ========================================
        # 7. MERGE PDFs
        # ========================================
        if not pdf_list:
            return JSONResponse(status_code=400, content={"erro": "Nenhum documento gerado"})

        nome_arquivo = nome.replace(" ", "_") + ".pdf"
        output_pdf = os.path.join(temp_dir, nome_arquivo)

        if len(pdf_list) == 1:
            shutil.copy2(pdf_list[0], output_pdf)
        else:
            merge_pdfs(pdf_list, output_pdf)

        # Retornar PDF
        return FileResponse(
            output_pdf,
            media_type="application/pdf",
            filename=nome_arquivo,
            headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"erro": str(e)})

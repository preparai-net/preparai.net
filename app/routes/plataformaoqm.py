"""
Rotas da Plataforma OQM — Preparação de banco de questões para upload.
Completamente separado do Fisiomed.
"""
import os
import re
import json
import shutil
import tempfile
import zipfile
import io
from typing import List
from copy import deepcopy
from lxml import etree
from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse

from app.generators.preparai import PreparaiProcessor
from app.generators.taxonomy import suggest_classification, get_subtemas_for_category, get_sub_subtemas, TAXONOMY

# Namespace OOXML
_W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

router = APIRouter(prefix="/api/oqm", tags=["PlataformaOQM"])

# Diretório de trabalho persistente por sessão
WORK_DIR = os.path.join(tempfile.gettempdir(), 'preparai_sessions')
os.makedirs(WORK_DIR, exist_ok=True)

# Processador ativo (uma sessão por vez)
_active_processor = None
_active_session = None


def _get_session_dir(session_id):
    d = os.path.join(WORK_DIR, session_id)
    os.makedirs(d, exist_ok=True)
    return d


def merge_docx_files(file_paths, output_path):
    """
    Junta múltiplos .docx num único arquivo via manipulação XML.
    Preserva imagens corretamente atualizando relationships (rId).

    Abordagem:
    1. Usa 1º arquivo como base
    2. Para cada arquivo extra:
       a. Lê relationships → mapeia rId → media file
       b. Copia media com nomes únicos para base
       c. Cria novos rIds no relationships da base
       d. Atualiza rIds nos parágrafos copiados
       e. Adiciona parágrafos ao body da base
    """
    if len(file_paths) == 1:
        shutil.copy2(file_paths[0], output_path)
        return

    RELS_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
    IMAGE_TYPE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/image'

    # Extrair base
    base_path = file_paths[0]
    with open(base_path, 'rb') as f:
        base_bytes = f.read()

    extract_dir = output_path + '_extract'
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)

    with zipfile.ZipFile(io.BytesIO(base_bytes), 'r') as zf:
        zip_entries = [info.filename for info in zf.infolist()]
        zf.extractall(extract_dir)

    # Parse document.xml da base
    doc_xml = os.path.join(extract_dir, 'word', 'document.xml')
    tree = etree.parse(doc_xml)
    root = tree.getroot()
    body = root.find(f'{_W}body')
    sect_pr = body.find(f'{_W}sectPr')

    # Guardar nsmap da base para propagar namespaces de extras se necessário
    base_nsmap = dict(root.nsmap)

    # Parse relationships da base
    rels_path = os.path.join(extract_dir, 'word', '_rels', 'document.xml.rels')
    rels_tree = etree.parse(rels_path)
    rels_root = rels_tree.getroot()

    # Encontrar o maior rId existente
    max_rid = 0
    for rel in rels_root.findall(f'{{{RELS_NS}}}Relationship'):
        rid_str = rel.get('Id', '')
        if rid_str.startswith('rId'):
            try:
                num = int(rid_str[3:])
                if num > max_rid:
                    max_rid = num
            except ValueError:
                pass

    media_counter = 1000
    rid_counter = max_rid + 1

    # Processar cada arquivo extra
    for extra_path in file_paths[1:]:
        with open(extra_path, 'rb') as f:
            extra_bytes = f.read()

        with zipfile.ZipFile(io.BytesIO(extra_bytes), 'r') as zf:
            # Parse document.xml do extra
            with zf.open('word/document.xml') as doc:
                extra_tree = etree.parse(doc)
            extra_root = extra_tree.getroot()
            extra_body = extra_root.find(f'{_W}body')

            # Propagar namespaces do extra para a base
            # Importante: se o 1º arquivo não tem imagens mas os outros têm,
            # namespaces como wp:, a:, pic: precisam existir no root
            for prefix, uri in extra_root.nsmap.items():
                if prefix and prefix not in base_nsmap:
                    # lxml não permite adicionar nsmap diretamente ao root,
                    # mas deepcopy preserva os namespaces dos elementos copiados
                    base_nsmap[prefix] = uri

            # Parse relationships do extra
            rid_map = {}  # old_rId -> new_rId (para atualizar refs nos parágrafos)
            try:
                with zf.open('word/_rels/document.xml.rels') as rels_f:
                    extra_rels = etree.parse(rels_f)
                extra_rels_root = extra_rels.getroot()

                HYPERLINK_TYPE = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink'

                for rel in extra_rels_root.findall(f'{{{RELS_NS}}}Relationship'):
                    old_rid = rel.get('Id', '')
                    rel_type = rel.get('Type', '')
                    target = rel.get('Target', '')
                    target_mode = rel.get('TargetMode', '')

                    # Processar imagens — copiar media com nome único
                    if rel_type == IMAGE_TYPE and target.startswith('media/'):
                        old_media_name = os.path.basename(target)
                        ext = os.path.splitext(old_media_name)[1]
                        new_media_name = f'merged_{media_counter}{ext}'
                        media_counter += 1

                        # Copiar o arquivo de media
                        media_dir = os.path.join(extract_dir, 'word', 'media')
                        os.makedirs(media_dir, exist_ok=True)
                        media_zip_path = f'word/media/{old_media_name}'
                        if media_zip_path in [i.filename for i in zf.infolist()]:
                            with zf.open(media_zip_path) as src:
                                with open(os.path.join(media_dir, new_media_name), 'wb') as dst:
                                    dst.write(src.read())
                            zip_entries.append(f'word/media/{new_media_name}')

                        # Criar novo rId e adicionar ao rels da base
                        new_rid = f'rId{rid_counter}'
                        rid_counter += 1
                        rid_map[old_rid] = new_rid

                        new_rel = etree.SubElement(rels_root, f'{{{RELS_NS}}}Relationship')
                        new_rel.set('Id', new_rid)
                        new_rel.set('Type', IMAGE_TYPE)
                        new_rel.set('Target', f'media/{new_media_name}')

                    # Processar hyperlinks — criar novo rId apontando para mesma URL
                    elif rel_type == HYPERLINK_TYPE:
                        new_rid = f'rId{rid_counter}'
                        rid_counter += 1
                        rid_map[old_rid] = new_rid

                        new_rel = etree.SubElement(rels_root, f'{{{RELS_NS}}}Relationship')
                        new_rel.set('Id', new_rid)
                        new_rel.set('Type', HYPERLINK_TYPE)
                        new_rel.set('Target', target)
                        if target_mode:
                            new_rel.set('TargetMode', target_mode)

            except KeyError:
                pass  # Arquivo sem relationships

        # Copiar parágrafos e atualizar rIds
        for child in extra_body:
            if child.tag == f'{_W}sectPr':
                continue
            new_elem = deepcopy(child)

            # Atualizar todas as referências de rId nos elementos copiados
            if rid_map:
                # Buscar em todos os atributos que contêm rId (r:embed, r:link, etc.)
                R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
                for attr_name in [f'{{{R_NS}}}embed', f'{{{R_NS}}}link', f'{{{R_NS}}}id']:
                    for elem in new_elem.iter():
                        old_val = elem.get(attr_name)
                        if old_val and old_val in rid_map:
                            elem.set(attr_name, rid_map[old_val])

            if sect_pr is not None:
                sect_pr.addprevious(new_elem)
            else:
                body.append(new_elem)

    # Salvar document.xml
    tree.write(doc_xml, xml_declaration=True, encoding='UTF-8', standalone=True)

    # Salvar relationships atualizado
    rels_tree.write(rels_path, xml_declaration=True, encoding='UTF-8', standalone=True)

    # Recriar ZIP
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        written = set()
        for entry in zip_entries:
            fpath = os.path.join(extract_dir, entry)
            if os.path.isfile(fpath) and entry not in written:
                zout.write(fpath, entry)
                written.add(entry)
        # Incluir arquivos novos (media adicionada, rels atualizado)
        for dirpath, dirs, files in os.walk(extract_dir):
            for fname in files:
                fpath = os.path.join(dirpath, fname)
                arcname = os.path.relpath(fpath, extract_dir)
                if arcname not in written:
                    zout.write(fpath, arcname)
                    written.add(arcname)

    # Validação pós-merge: contar drawings nos originais vs output
    # Inspirado na seção A3 do prompt de autovalidação PREPARAI
    try:
        with zipfile.ZipFile(output_path, 'r') as zf:
            out_doc = zf.open('word/document.xml').read()
        out_root = etree.fromstring(out_doc)
        out_drawings = out_root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing')
        # Fallback: buscar no namespace drawingML
        if not out_drawings:
            out_drawings = [e for e in out_root.iter() if 'drawing' in e.tag.lower()]

        # Contar drawings nos originais
        total_orig_drawings = 0
        for fp in file_paths:
            with zipfile.ZipFile(fp, 'r') as zf:
                orig_doc = zf.open('word/document.xml').read()
            orig_root = etree.fromstring(orig_doc)
            orig_d = orig_root.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing')
            if not orig_d:
                orig_d = [e for e in orig_root.iter() if 'drawing' in e.tag.lower()]
            total_orig_drawings += len(orig_d)

        if len(out_drawings) != total_orig_drawings:
            print(f"⚠️ MERGE WARNING: drawings originais={total_orig_drawings}, output={len(out_drawings)}")
        else:
            print(f"✅ MERGE OK: {len(out_drawings)} drawings preservados")

        # Verificar que todos rId:embed no output existem no rels
        with zipfile.ZipFile(output_path, 'r') as zf:
            rels_content = zf.open('word/_rels/document.xml.rels').read()
        rels_root_check = etree.fromstring(rels_content)
        valid_rids = set()
        for rel in rels_root_check.findall(f'{{{RELS_NS}}}Relationship'):
            valid_rids.add(rel.get('Id', ''))

        R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        missing_rids = []
        for elem in out_root.iter():
            rid_val = elem.get(f'{{{R_NS}}}embed')
            if rid_val and rid_val not in valid_rids:
                missing_rids.append(rid_val)
        if missing_rids:
            print(f"⚠️ MERGE WARNING: rIds sem relationship: {missing_rids}")
        else:
            print(f"✅ MERGE OK: todos os rId:embed têm relationship válida")
    except Exception as e:
        print(f"⚠️ MERGE: Validação pós-merge falhou: {e}")

    # Limpar
    shutil.rmtree(extract_dir, ignore_errors=True)


@router.post("/upload")
async def upload_docx(files: List[UploadFile] = File(...)):
    """
    Fase 0+1: Upload de 1 ou mais .docx → análise individual de cada arquivo.
    Cada arquivo é tratado como 1 questão independente.
    NÃO faz merge — processa individualmente.
    """
    global _active_session

    # Criar sessão
    import uuid
    session_id = str(uuid.uuid4())[:8]
    session_dir = _get_session_dir(session_id)

    # Salvar todos os arquivos
    file_entries = []  # Lista de { 'original_name', 'input_path', 'index' }
    all_questions = []
    all_issues = []
    total_media = 0

    for idx, file in enumerate(files):
        fname = file.filename or f'questao_{idx}.docx'
        # Sanitizar nome
        safe_fname = re.sub(r'[^\w\s\-\.\[\]\(\)]', '_', fname)
        fpath = os.path.join(session_dir, f'input_{idx}_{safe_fname}')
        with open(fpath, 'wb') as f:
            content = await file.read()
            f.write(content)

        file_entries.append({
            'index': idx,
            'original_name': fname,
            'input_path': fpath,
        })

    # Analisar cada arquivo individualmente
    for entry in file_entries:
        try:
            work_sub = os.path.join(session_dir, f'work_{entry["index"]}')
            processor = PreparaiProcessor(entry['input_path'], work_dir=work_sub)
            analysis = processor.phase0_analyze()
            audit = processor.phase1_audit()

            for q in analysis['questions']:
                q['_file_index'] = entry['index']
                q['_file_name'] = entry['original_name']
                # Separar categoria e subtema para exibição na UI
                cat_full = q['categoria'] or ''
                if ' | ' in cat_full:
                    cat_parts = cat_full.split(' | ', 1)
                    cat_only = cat_parts[0].strip()
                    sub_only = cat_parts[1].strip()
                elif ' - ' in cat_full:
                    cat_parts = cat_full.split(' - ', 1)
                    cat_only = cat_parts[0].strip()
                    sub_only = cat_parts[1].strip()
                else:
                    cat_only = cat_full.strip()
                    sub_only = ''

                # Sugestão local de taxonomia (keyword matching)
                tax_method = 'original' if cat_only else 'none'
                if not cat_only or not sub_only:
                    resolucao_text = q.get('resolucao', '')
                    suggestion = suggest_classification(
                        q['enunciado'], q.get('alternativas', []),
                        cat_only, resolucao_text
                    )
                    if suggestion['confidence'] > 0 and suggestion['categoria']:
                        if not cat_only:
                            cat_only = suggestion['categoria']
                            tax_method = 'local'
                        if not sub_only and suggestion['subtema']:
                            sub_only = suggestion['subtema']
                            tax_method = 'local'

                all_questions.append({
                    'number': q['number'],
                    'header': q['original_header'],
                    'categoria': cat_only,
                    'subtema': sub_only,
                    'gabarito': q['gabarito'],
                    'has_highlight': q['has_highlight'],
                    'has_resolucao_bold': q['has_resolucao_bold'],
                    'has_referencias': q['has_referencias'],
                    'ref_count': q['ref_count'],
                    'accent_issues': q['accent_issues'],
                    'enunciado_preview': q['enunciado'][:150].strip(),
                    'file_index': entry['index'],
                    'file_name': entry['original_name'],
                    'taxonomy_method': tax_method,
                })

            total_media += analysis['media_files']

            for iss in audit.get('issues', []):
                iss['file_name'] = entry['original_name']
                all_issues.append(iss)

        except Exception as e:
            import traceback
            traceback.print_exc()
            all_questions.append({
                'number': 0,
                'header': f'ERRO: {entry["original_name"]}',
                'categoria': '',
                'subtema': '',
                'gabarito': '',
                'has_highlight': False,
                'has_resolucao_bold': False,
                'has_referencias': False,
                'ref_count': 0,
                'accent_issues': [],
                'enunciado_preview': str(e)[:150],
                'file_index': entry['index'],
                'file_name': entry['original_name'],
                'error': str(e),
            })

    _active_session = {
        'id': session_id,
        'dir': session_dir,
        'file_entries': file_entries,
        'total_questions': len(all_questions),
    }

    # Calcular summary de auditoria a partir das questões analisadas
    valid_questions = [q for q in all_questions if not q.get('error')]
    audit_summary = {
        'sem_highlight': sum(1 for q in valid_questions if not q.get('has_highlight')),
        'sem_grau': 0,  # Dificuldade é definida pelo usuário na fase de config
        'acentos': sum(1 for q in valid_questions if q.get('accent_issues')),
        'refs_multiplas': sum(1 for q in valid_questions if q.get('ref_count', 0) > 1),
    }

    return JSONResponse(content={
        'session_id': session_id,
        'files_count': len(file_entries),
        'files_names': [e['original_name'] for e in file_entries],
        'analysis': {
            'total_questions': len(all_questions),
            'duplicates': [],
            'repeated_numbers': [],
            'media_files': total_media,
        },
        'audit': {
            'issues': all_issues,
            'summary': audit_summary,
        },
        'questions': all_questions,
    })


@router.post("/process")
async def process_docx(request: Request):
    """
    Fases 3-5: Processa cada arquivo individualmente.
    Gera um _OQM.docx para cada arquivo de entrada.
    Recebe config com IDs OQM, dificuldades, categorias e flags.
    """
    global _active_session

    if _active_session is None or 'file_entries' not in _active_session:
        return JSONResponse(status_code=400, content={'erro': 'Nenhum arquivo carregado. Faça upload primeiro.'})

    try:
        dados = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={'erro': 'JSON inválido'})

    # Juntar categoria + subtema no formato "Cat | Sub" para o preparai.py
    raw_cats = {int(k): v for k, v in dados.get('categories', {}).items()}
    raw_subs = {int(k): v for k, v in dados.get('subtemas', {}).items()}
    merged_categories = {}
    all_keys = set(list(raw_cats.keys()) + list(raw_subs.keys()))
    for qnum in all_keys:
        cat = raw_cats.get(qnum, '').strip()
        sub = raw_subs.get(qnum, '').strip()
        if cat and sub:
            merged_categories[qnum] = f'{cat} | {sub}'
        elif cat:
            merged_categories[qnum] = cat
        elif sub:
            merged_categories[qnum] = sub

    config = {
        'start_oqm': dados.get('start_oqm', 1),
        'difficulties': {int(k): v for k, v in dados.get('difficulties', {}).items()},
        'categories': merged_categories,
        # Flags de classificação
        'apply_categories': dados.get('apply_categories', True),
        'apply_subtemas': dados.get('apply_subtemas', True),
        'apply_difficulties': dados.get('apply_difficulties', True),
        # Flags de formatação
        'apply_accents': dados.get('apply_accents', True),
        'apply_highlight': dados.get('apply_highlight', True),
        'apply_bold_resolucao': dados.get('apply_bold_resolucao', True),
        'apply_limit_refs': dados.get('apply_limit_refs', True),
        # Flags de estrutura
        'apply_insert_tags': dados.get('apply_insert_tags', True),
        'apply_video': dados.get('apply_video', True),
        'apply_remove_separators': dados.get('apply_remove_separators', True),
        'apply_page_breaks': dados.get('apply_page_breaks', True),
    }

    file_entries = _active_session['file_entries']
    output_files = []  # Lista de { 'index', 'original_name', 'output_name', 'output_path', 'validation' }
    oqm_counter = config['start_oqm']
    all_validations = []

    for entry in file_entries:
        try:
            work_sub = os.path.join(_active_session['dir'], f'work_{entry["index"]}')

            # Criar config individual com OQM sequencial
            file_config = dict(config)
            file_config['start_oqm'] = oqm_counter

            # Processar
            processor = PreparaiProcessor(entry['input_path'], work_dir=work_sub)

            # Gerar nome de saída: nome_original_OQM.docx
            orig_name = entry['original_name']
            if orig_name.lower().endswith('.docx'):
                output_name = orig_name[:-5] + '_OQM.docx'
            else:
                output_name = orig_name + '_OQM.docx'

            output_path = os.path.join(_active_session['dir'], f'output_{entry["index"]}_{output_name}')
            result = processor.process(output_path, file_config)

            # Contar quantas questões este arquivo tinha para incrementar o OQM counter
            q_count = result['validation'].get('total', 1)
            oqm_counter += q_count

            output_entry = {
                'index': entry['index'],
                'original_name': orig_name,
                'output_name': output_name,
                'output_path': output_path,
                'validation': result['validation'],
            }
            output_files.append(output_entry)
            all_validations.append({
                'file_name': output_name,
                'original_name': orig_name,
                'index': entry['index'],
                'validation': result['validation'],
            })

            print(f"✅ Processado: {orig_name} → {output_name}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            output_files.append({
                'index': entry['index'],
                'original_name': entry['original_name'],
                'output_name': f'ERRO_{entry["original_name"]}',
                'output_path': None,
                'error': str(e),
            })
            all_validations.append({
                'file_name': entry['original_name'],
                'original_name': entry['original_name'],
                'index': entry['index'],
                'error': str(e),
            })
            print(f"❌ Erro: {entry['original_name']}: {e}")

    _active_session['output_files'] = output_files

    return JSONResponse(content={
        'success': True,
        'total_files': len(output_files),
        'files': [{
            'index': f['index'],
            'original_name': f['original_name'],
            'output_name': f['output_name'],
            'error': f.get('error'),
        } for f in output_files],
        'validations': all_validations,
    })


@router.post("/semantic-audit")
async def semantic_audit(request: Request):
    """
    Fase 6: Auditoria semântica via API Claude.
    Classifica dificuldade + audita categorias/subtemas.
    """
    global _active_session

    if _active_session is None or 'file_entries' not in _active_session:
        return JSONResponse(status_code=400, content={'erro': 'Nenhum arquivo carregado.'})

    try:
        dados = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={'erro': 'JSON inválido'})

    api_key = dados.get('api_key', '')
    if not api_key:
        return JSONResponse(status_code=400, content={'erro': 'API key do Claude é obrigatória.'})

    # Reconstruir lista de questões a partir dos arquivos
    questions = []
    for entry in _active_session['file_entries']:
        try:
            work_sub = os.path.join(_active_session['dir'], f'audit_{entry["index"]}')
            proc = PreparaiProcessor(entry['input_path'], work_dir=work_sub)
            analysis = proc.phase0_analyze()
            questions.extend(proc.questions)
        except Exception:
            pass

    if not questions:
        return JSONResponse(status_code=400, content={'erro': 'Nenhuma questão encontrada.'})

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        results = []

        # Processar em lote (todas as questões num único prompt para economizar)
        questions_text = []
        for q in questions:
            alt_text = '\n'.join(q['alternativas']) if q['alternativas'] else '(sem alternativas)'
            questions_text.append(
                f"--- QUESTÃO {q['number']} ---\n"
                f"CATEGORIA ATUAL: {q['categoria']}\n"
                f"ENUNCIADO: {q['enunciado'][:500]}\n"
                f"ALTERNATIVAS:\n{alt_text}\n"
                f"GABARITO: {q['gabarito']}\n"
            )

        all_questions = '\n'.join(questions_text)

        prompt = f"""Você é um professor de ortopedia especialista em prova TEOT. Analise as questões abaixo e para CADA uma, responda em JSON.

REGRAS DE CLASSIFICAÇÃO DE DIFICULDADE:
- Muito fácil: fato decorado, número redondo, resposta quase óbvia
- Fácil: associação direta conceito↔técnica conhecida, cobrado com frequência (ex: "Kocher = ECU + ancôneo")
- Mediano: conhecimento técnico TEOT padrão, exige raciocínio mas está na média
- Difícil: detalhe anatômico fino, caso clínico complexo, raciocínio de exclusão
- Muito Difícil: conceito raro, sinal clínico pouco cobrado, técnica cirúrgica super-específica

REGRAS DE CATEGORIA:
- Formato: "Categoria | Subtema" (ex: "Joelho | Vias de Acesso")
- Cotovelo é agrupado dentro de Ombro (ex: "Ombro | Artroplastia do Cotovelo")
- Básicas: trombose, torniquete, enxertos ósseos, antibióticos, cicatrização
- Pediatria é separado de Trauma/Ortopedia de adulto
- Subtema deve ser específico e capitalizado corretamente

Responda APENAS com JSON válido neste formato:
{{
  "questions": [
    {{
      "number": 1,
      "difficulty": "Mediano",
      "category_ok": true,
      "suggested_category": "Joelho",
      "suggested_subtema": "Vias de Acesso",
      "category_reason": "motivo da sugestão se category_ok=false"
    }}
  ]
}}

QUESTÕES:
{all_questions}"""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse resposta
        response_text = message.content[0].text

        # Extrair JSON da resposta
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            audit_result = json.loads(json_match.group())
        else:
            audit_result = {"questions": [], "error": "Não foi possível parsear resposta da API"}

        return JSONResponse(content={
            'success': True,
            'audit': audit_result,
        })

    except ImportError:
        return JSONResponse(status_code=500, content={
            'erro': 'Biblioteca anthropic não instalada. Execute: pip install anthropic'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'erro': str(e)})


@router.get("/download/{file_index}")
async def download_single(file_index: int):
    """Download de um arquivo processado individual pelo índice."""
    global _active_session

    if _active_session is None or 'output_files' not in _active_session:
        return JSONResponse(status_code=400, content={'erro': 'Nenhum arquivo processado.'})

    output_files = _active_session['output_files']

    # Buscar pelo index
    target = None
    for f in output_files:
        if f['index'] == file_index:
            target = f
            break

    if target is None:
        return JSONResponse(status_code=404, content={'erro': f'Arquivo #{file_index} não encontrado.'})

    if target.get('error') or not target.get('output_path'):
        return JSONResponse(status_code=400, content={'erro': f'Arquivo #{file_index} teve erro no processamento.'})

    output_path = target['output_path']
    output_name = target['output_name']

    if not os.path.exists(output_path):
        return JSONResponse(status_code=404, content={'erro': 'Arquivo não encontrado no disco.'})

    return FileResponse(
        output_path,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=output_name,
        headers={'Content-Disposition': f'attachment; filename="{output_name}"'}
    )


@router.get("/download-all")
async def download_all():
    """Download de TODOS os arquivos processados como ZIP."""
    global _active_session

    if _active_session is None or 'output_files' not in _active_session:
        return JSONResponse(status_code=400, content={'erro': 'Nenhum arquivo processado.'})

    output_files = _active_session['output_files']
    valid_files = [f for f in output_files if f.get('output_path') and not f.get('error')]

    if not valid_files:
        return JSONResponse(status_code=400, content={'erro': 'Nenhum arquivo processado com sucesso.'})

    # Criar ZIP
    zip_name = f'questoes_OQM_{len(valid_files)}_arquivos.zip'
    zip_path = os.path.join(_active_session['dir'], zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in valid_files:
            if os.path.exists(f['output_path']):
                zf.write(f['output_path'], f['output_name'])

    return FileResponse(
        zip_path,
        media_type='application/zip',
        filename=zip_name,
        headers={'Content-Disposition': f'attachment; filename="{zip_name}"'}
    )


# Manter compatibilidade com endpoint antigo
@router.get("/download")
async def download_result():
    """Compatibilidade: redireciona para download-all."""
    return await download_all()


@router.get("/taxonomy")
async def get_taxonomy():
    """Retorna a taxonomia completa para popular dropdowns no frontend."""
    categories = list(TAXONOMY.keys())
    subtemas = {}
    for cat in categories:
        subtemas[cat] = get_subtemas_for_category(cat)
    return JSONResponse(content={
        'categories': categories,
        'subtemas': subtemas,
    })


# ==============================================================
# ABA 2: INSERIR VÍDEOS
# ==============================================================
_video_session = {}


@router.post("/video/upload-questions")
async def video_upload_questions(files: List[UploadFile] = File(...)):
    """Upload de 1 ou mais .docx de questões (já com OQM IDs)."""
    global _video_session
    import uuid

    session_id = str(uuid.uuid4())[:8]
    session_dir = _get_session_dir('video_' + session_id)

    # Salvar todos os arquivos
    saved_paths = []
    filenames = []
    for file in files:
        fname = file.filename or f'questoes_{len(saved_paths)}.docx'
        filenames.append(fname)
        fpath = os.path.join(session_dir, f'vq_{len(saved_paths)}_{fname}')
        with open(fpath, 'wb') as f:
            content = await file.read()
            f.write(content)
        saved_paths.append(fpath)

    # Merge se múltiplos
    if len(saved_paths) == 1:
        input_path = saved_paths[0]
    else:
        input_path = os.path.join(session_dir, 'questoes_combinadas.docx')
        merge_docx_files(saved_paths, input_path)

    try:
        with zipfile.ZipFile(input_path, 'r') as zf:
            with zf.open('word/document.xml') as doc:
                tree = etree.parse(doc)
        body = tree.getroot().find(f'{_W}body')
        paras = body.findall(f'{_W}p')

        # Contar questões (linhas que casam OQMxxxxx)
        count = 0
        for p in paras:
            runs = p.findall(f'.//{_W}r')
            text = ''.join(r.findtext(f'{_W}t', '') for r in runs).strip()
            if re.match(r'OQM\d{5}', text):
                count += 1

        _video_session = {
            'id': session_id,
            'dir': session_dir,
            'questions_path': input_path,
            'questions_count': count,
            'files_count': len(saved_paths),
        }

        return JSONResponse(content={'count': count, 'files_count': len(saved_paths)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'erro': str(e)})


@router.post("/video/upload-videos")
async def video_upload_videos(file: UploadFile = File(...)):
    """Upload do .docx de vídeos (IDs + URLs)."""
    global _video_session
    import zipfile
    from lxml import etree

    if not _video_session.get('questions_path'):
        return JSONResponse(status_code=400, content={'erro': 'Envie o arquivo de questões primeiro.'})

    video_path = os.path.join(_video_session['dir'], file.filename or 'videos.docx')
    with open(video_path, 'wb') as f:
        content = await file.read()
        f.write(content)

    try:
        W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        with zipfile.ZipFile(video_path, 'r') as zf:
            with zf.open('word/document.xml') as doc:
                tree = etree.parse(doc)
        body = tree.getroot().find(f'{W}body')
        paras = body.findall(f'{W}p')

        # Parsear pares ID → URL
        video_map = {}
        current_id = None
        for p in paras:
            runs = p.findall(f'.//{W}r')
            text = ''.join(r.findtext(f'{W}t', '') for r in runs).strip()
            if re.match(r'OQM\d{5}', text):
                current_id = text
            elif current_id and text.startswith('http'):
                video_map[current_id] = text
                current_id = None

        _video_session['videos_path'] = video_path
        _video_session['video_map'] = video_map

        return JSONResponse(content={'count': len(video_map)})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'erro': str(e)})


@router.post("/video/merge")
async def video_merge():
    """Merge: insere [VÍDEO] + URL nas questões, casando por OQM ID."""
    global _video_session
    import zipfile, io
    from lxml import etree
    from copy import deepcopy

    if not _video_session.get('video_map') or not _video_session.get('questions_path'):
        return JSONResponse(status_code=400, content={'erro': 'Envie ambos os arquivos primeiro.'})

    questions_path = _video_session['questions_path']
    video_map = _video_session['video_map']

    try:
        W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        NSMAP = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

        # Ler o DOCX
        with open(questions_path, 'rb') as f:
            docx_bytes = f.read()

        with zipfile.ZipFile(io.BytesIO(docx_bytes), 'r') as zf:
            zip_entries = [info.filename for info in zf.infolist()]
            extract_dir = os.path.join(_video_session['dir'], 'extract_video')
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            zf.extractall(extract_dir)

        doc_xml = os.path.join(extract_dir, 'word', 'document.xml')
        tree = etree.parse(doc_xml)
        root = tree.getroot()
        body = root.find(f'{W}body')
        paras = list(body.findall(f'{W}p'))

        def get_text(p):
            return ''.join(r.findtext(f'{W}t', '') for r in p.findall(f'.//{W}r')).strip()

        def make_para(text, bold=False, underline=False, gray=False):
            """Cria um parágrafo simples."""
            p = etree.SubElement(body, f'{W}p')  # temporário, será movido
            body.remove(p)
            r = etree.SubElement(p, f'{W}r')
            rPr = etree.SubElement(r, f'{W}rPr')
            if bold:
                etree.SubElement(rPr, f'{W}b')
            if underline:
                etree.SubElement(rPr, f'{W}u', {f'{W}val': 'single'})
            if gray:
                color = etree.SubElement(rPr, f'{W}color')
                color.set(f'{W}val', '808080')
            sz = etree.SubElement(rPr, f'{W}sz')
            sz.set(f'{W}val', '24')
            t = etree.SubElement(r, f'{W}t')
            t.text = text
            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            return p

        def make_empty():
            p = etree.SubElement(body, f'{W}p')
            body.remove(p)
            return p

        # Encontrar questões e inserir vídeos
        matched = 0
        not_found_ids = []
        processed_ids = set()

        # Iterar de trás pra frente para não perder índices
        i = len(paras) - 1
        while i >= 0:
            text = get_text(paras[i])
            if re.match(r'OQM\d{5}', text) and text in video_map and text not in processed_ids:
                oqm_id = text
                processed_ids.add(oqm_id)

                # Verificar se já tem [VÍDEO] — procurar até próxima questão ou fim
                has_video = False
                last_para_of_question = i
                for j in range(i + 1, len(paras)):
                    jtext = get_text(paras[j])
                    if '[NOME DA QUESTÃO]' in jtext:
                        break
                    if re.match(r'OQM\d{5}', jtext) and jtext != oqm_id:
                        break
                    last_para_of_question = j
                    if '[VÍDEO]' in jtext:
                        has_video = True
                        # Substituir a URL na próxima linha
                        if j + 1 < len(paras):
                            url_para = paras[j + 1]
                            # Limpar runs existentes
                            for run in url_para.findall(f'{W}r'):
                                url_para.remove(run)
                            # Adicionar nova URL
                            r = etree.SubElement(url_para, f'{W}r')
                            rPr = etree.SubElement(r, f'{W}rPr')
                            etree.SubElement(rPr, f'{W}u', {f'{W}val': 'single'})
                            sz = etree.SubElement(rPr, f'{W}sz')
                            sz.set(f'{W}val', '24')
                            t = etree.SubElement(r, f'{W}t')
                            t.text = video_map[oqm_id]
                            t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                        matched += 1
                        break

                if not has_video:
                    # Inserir [VÍDEO] + URL após último parágrafo da questão
                    anchor = paras[last_para_of_question]
                    # Inserir em ordem reversa (addnext coloca logo após)
                    url_p = make_para(video_map[oqm_id], underline=True)
                    video_tag_p = make_para('[VÍDEO]', bold=True, gray=True)
                    empty_p = make_empty()

                    anchor.addnext(url_p)
                    anchor.addnext(video_tag_p)
                    anchor.addnext(empty_p)
                    matched += 1

            i -= 1

        # IDs no video_map que não foram encontrados
        for vid in video_map:
            if vid not in processed_ids:
                not_found_ids.append(vid)

        # Salvar
        tree.write(doc_xml, xml_declaration=True, encoding='UTF-8', standalone=True)

        output_name = os.path.basename(questions_path).replace('.docx', '_COM_VIDEOS.docx')
        output_path = os.path.join(_video_session['dir'], output_name)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for entry in zip_entries:
                fpath = os.path.join(extract_dir, entry)
                if os.path.isfile(fpath):
                    zf.write(fpath, entry)

        _video_session['output_path'] = output_path
        _video_session['output_name'] = output_name

        return JSONResponse(content={
            'matched': matched,
            'not_found': len(not_found_ids),
            'missing_ids': not_found_ids,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={'erro': str(e)})


@router.get("/video/download")
async def video_download():
    """Download do arquivo com vídeos inseridos."""
    global _video_session

    if not _video_session.get('output_path'):
        return JSONResponse(status_code=400, content={'erro': 'Nenhum arquivo processado.'})

    return FileResponse(
        _video_session['output_path'],
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename=_video_session['output_name'],
        headers={'Content-Disposition': f'attachment; filename="{_video_session["output_name"]}"'}
    )

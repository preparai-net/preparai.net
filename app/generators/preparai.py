"""
Engine de processamento PREPARAI — Preparação de Banco de Questões para upload.

Fases implementadas:
  0. Recepção e detecção de duplicatas
  1. Auditoria estrutural
  4. Aplicação dos 12 ajustes sistemáticos (via lxml)
  5. Validação automática (14 critérios)

Regras técnicas:
  - shutil.copy2 → zipfile.extractall → lxml.etree.parse → edição → zipfile.ZIP_DEFLATED
  - Preservar ordem ZIP original (infolist)
  - Imagens INTOCÁVEIS (nunca alterar w:drawing)
  - Runs fragmentados: juntar texto do parágrafo, substituir, redistribuir
"""
import os
import re
import shutil
import zipfile
import hashlib
import unicodedata
from copy import deepcopy
from lxml import etree

# Namespaces OOXML
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
WP = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

# Dicionário de correção de acentos
ACCENT_FIXES = {
    'QUESTAO': 'QUESTÃO',
    'Resolucao': 'Resolução',
    'REFERENCIAS BIBLIOGRAFICAS': 'REFERÊNCIAS BIBLIOGRÁFICAS',
    'REFERENCIAS': 'REFERÊNCIAS',
    'BIBLIOGRAFICAS': 'BIBLIOGRÁFICAS',
    'Basicas': 'Básicas',
    'BASICAS': 'BÁSICAS',
}

# Escala de dificuldade válida
VALID_DIFFICULTIES = ['Muito fácil', 'Fácil', 'Mediano', 'Difícil', 'Muito Difícil']

# Tags obrigatórias (na ordem correta)
REQUIRED_TAGS = [
    '[NOME DA QUESTÃO]',
    '[CATEGORIA | SUBTEMA]',
    '[GRAU DE DIFICULDADE]',
    '[ENUNCIADO]',
    '[ALTERNATIVAS, SENDO A ALTERNATIVA PINTADA DE AMARELO A CORRETA]',
    '[COMENTÁRIOS]',
    '[VÍDEO]',
]

VIDEO_URL = 'https://www.youtube.com/@ortopediaoqm/'


# =====================================================
# UTILITÁRIOS
# =====================================================

def get_para_text(para):
    """Extrai texto completo de um parágrafo, juntando todos os runs."""
    parts = []
    for t in para.findall(f'.//{W}t'):
        if t.text:
            parts.append(t.text)
    return ''.join(parts)


def has_drawing(para):
    """Verifica se parágrafo contém imagem/drawing."""
    ns_drawing = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}drawing'
    # Checar w:drawing
    if para.findall(f'.//{W}drawing'):
        return True
    # Checar mc:AlternateContent com drawings
    for child in para.iter():
        if 'drawing' in child.tag.lower():
            return True
    return False


def normalize_text(text):
    """Normaliza texto para comparação (sem acento, lowercase, collapse whitespace)."""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def make_empty_para():
    """Cria parágrafo vazio (linha em branco entre tópicos)."""
    p = etree.Element(f'{W}p')
    pPr = etree.SubElement(p, f'{W}pPr')
    sp = etree.SubElement(pPr, f'{W}spacing')
    sp.set(f'{W}after', '0')
    sp.set(f'{W}line', '240')
    sp.set(f'{W}lineRule', 'auto')
    jc = etree.SubElement(pPr, f'{W}jc')
    jc.set(f'{W}val', 'both')
    return p


def make_tag_para(tag_text, page_break=False):
    """Cria parágrafo com tag em colchetes (cinza #808080, sem negrito)."""
    p = etree.Element(f'{W}p')
    pPr = etree.SubElement(p, f'{W}pPr')
    if page_break:
        etree.SubElement(pPr, f'{W}pageBreakBefore')
    sp = etree.SubElement(pPr, f'{W}spacing')
    sp.set(f'{W}after', '0')
    sp.set(f'{W}line', '240')
    sp.set(f'{W}lineRule', 'auto')
    jc = etree.SubElement(pPr, f'{W}jc')
    jc.set(f'{W}val', 'both')

    r = etree.SubElement(p, f'{W}r')
    rPr = etree.SubElement(r, f'{W}rPr')
    color = etree.SubElement(rPr, f'{W}color')
    color.set(f'{W}val', '808080')
    t = etree.SubElement(r, f'{W}t')
    t.set(XML_SPACE, 'preserve')
    t.text = tag_text
    return p


def make_text_para(text, bold=False, underline=False, color=None):
    """Cria parágrafo com texto simples."""
    p = etree.Element(f'{W}p')
    pPr = etree.SubElement(p, f'{W}pPr')
    sp = etree.SubElement(pPr, f'{W}spacing')
    sp.set(f'{W}after', '0')
    sp.set(f'{W}line', '240')
    sp.set(f'{W}lineRule', 'auto')
    jc = etree.SubElement(pPr, f'{W}jc')
    jc.set(f'{W}val', 'both')

    r = etree.SubElement(p, f'{W}r')
    rPr = etree.SubElement(r, f'{W}rPr')
    if bold:
        etree.SubElement(rPr, f'{W}b')
    if underline:
        u = etree.SubElement(rPr, f'{W}u')
        u.set(f'{W}val', 'single')
    if color:
        c = etree.SubElement(rPr, f'{W}color')
        c.set(f'{W}val', color)
    t = etree.SubElement(r, f'{W}t')
    t.set(XML_SPACE, 'preserve')
    t.text = text
    return p


def set_highlight_yellow(para):
    """Adiciona highlight amarelo em todos os runs de um parágrafo."""
    for run in para.findall(f'{W}r'):
        rPr = run.find(f'{W}rPr')
        if rPr is None:
            rPr = etree.SubElement(run, f'{W}rPr')
            run.insert(0, rPr)
        # Remover highlight existente
        for hl in rPr.findall(f'{W}highlight'):
            rPr.remove(hl)
        # Adicionar amarelo
        hl = etree.SubElement(rPr, f'{W}highlight')
        hl.set(f'{W}val', 'yellow')


def remove_highlight(para):
    """Remove highlight de todos os runs de um parágrafo."""
    for run in para.findall(f'{W}r'):
        rPr = run.find(f'{W}rPr')
        if rPr is not None:
            for hl in rPr.findall(f'{W}highlight'):
                rPr.remove(hl)


def set_bold(para):
    """Adiciona negrito em todos os runs de um parágrafo."""
    for run in para.findall(f'{W}r'):
        rPr = run.find(f'{W}rPr')
        if rPr is None:
            rPr = etree.SubElement(run, f'{W}rPr')
            run.insert(0, rPr)
        if rPr.find(f'{W}b') is None:
            etree.SubElement(rPr, f'{W}b')


def remove_bold(para):
    """Remove negrito de todos os runs de um parágrafo."""
    for run in para.findall(f'{W}r'):
        rPr = run.find(f'{W}rPr')
        if rPr is not None:
            for b in rPr.findall(f'{W}b'):
                rPr.remove(b)


def set_color_gray(para):
    """Define cor cinza #808080 em todos os runs de um parágrafo."""
    for run in para.findall(f'{W}r'):
        rPr = run.find(f'{W}rPr')
        if rPr is None:
            rPr = etree.SubElement(run, f'{W}rPr')
            run.insert(0, rPr)
        for c in rPr.findall(f'{W}color'):
            rPr.remove(c)
        color = etree.SubElement(rPr, f'{W}color')
        color.set(f'{W}val', '808080')


def fix_accents_in_para(para):
    """
    Corrige acentos preservando formatação de cada run.

    Estratégia:
    1. Tenta corrigir run por run (preserva 100% da formatação)
    2. Só se o texto errado estiver fragmentado entre runs (ex: run1="QUEST" + run2="AO"),
       aí junta no 1º run — caso raro mas necessário.
    """
    runs = para.findall(f'{W}r')
    if not runs:
        return False

    changed = False

    # Estratégia 1: corrigir dentro de cada run individual
    for run in runs:
        for t_elem in run.findall(f'{W}t'):
            if t_elem.text:
                original = t_elem.text
                fixed = original
                for wrong, correct in ACCENT_FIXES.items():
                    fixed = fixed.replace(wrong, correct)
                if fixed != original:
                    t_elem.text = fixed
                    t_elem.set(XML_SPACE, 'preserve')
                    changed = True

    if changed:
        return True

    # Estratégia 2: texto fragmentado entre runs — inevitável juntar
    full_text = get_para_text(para)
    if not full_text:
        return False

    fixed_full = full_text
    for wrong, correct in ACCENT_FIXES.items():
        fixed_full = fixed_full.replace(wrong, correct)

    if fixed_full == full_text:
        return False

    # Juntar no 1º run (só acontece quando o texto errado cruza runs)
    first_t = None
    for run in runs:
        for t_elem in run.findall(f'{W}t'):
            if first_t is None:
                first_t = t_elem
                t_elem.text = fixed_full
                t_elem.set(XML_SPACE, 'preserve')
            else:
                t_elem.text = ''
    return True


def set_para_text_preserve_format(para, new_text):
    """
    Define novo texto no parágrafo preservando a formatação do 1º run.

    Se o parágrafo tem um único run (caso mais comum para categorias),
    simplesmente altera o texto. Se tem múltiplos runs, coloca tudo
    no 1º run preservando suas propriedades (rPr) e esvazia os demais.
    """
    runs = para.findall(f'{W}r')
    if not runs:
        return
    first_t = None
    for run in runs:
        for t_elem in run.findall(f'{W}t'):
            if first_t is None:
                first_t = t_elem
                t_elem.text = new_text
                t_elem.set(XML_SPACE, 'preserve')
            else:
                t_elem.text = ''


def remove_page_break_before(para):
    """Remove pageBreakBefore de um parágrafo."""
    pPr = para.find(f'{W}pPr')
    if pPr is not None:
        for pb in pPr.findall(f'{W}pageBreakBefore'):
            pPr.remove(pb)


def remove_br_page(para):
    """Remove <w:br w:type="page"/> de um parágrafo."""
    for run in para.findall(f'{W}r'):
        for br in run.findall(f'{W}br'):
            if br.get(f'{W}type') == 'page':
                run.remove(br)


def is_underscore_separator(text):
    """Verifica se texto é um separador de underscores."""
    return bool(re.match(r'^_{5,}$', text.strip()))


# =====================================================
# CLASSE PRINCIPAL
# =====================================================

class PreparaiProcessor:
    """Processador PREPARAI para preparação de banco de questões."""

    def __init__(self, docx_path, work_dir='/tmp/preparai_work'):
        self.docx_path = docx_path
        self.work_dir = work_dir
        self.extract_dir = os.path.join(work_dir, 'extracted')
        self.tree = None
        self.body = None
        self.questions = []  # Lista de dicts com dados de cada questão
        self.zip_entries = []  # Preservar ordem do ZIP original
        self.media_hashes = {}  # MD5 das imagens originais

    def _extract(self):
        """Extrai DOCX preservando ordem do ZIP."""
        # Ler bytes ANTES de limpar diretórios (o arquivo pode estar dentro de work_dir)
        with open(self.docx_path, 'rb') as f:
            docx_bytes = f.read()

        if os.path.exists(self.extract_dir):
            shutil.rmtree(self.extract_dir)
        os.makedirs(self.extract_dir, exist_ok=True)
        os.makedirs(self.work_dir, exist_ok=True)

        original_copy = os.path.join(self.work_dir, 'original.docx')
        with open(original_copy, 'wb') as f:
            f.write(docx_bytes)

        import io
        with zipfile.ZipFile(io.BytesIO(docx_bytes), 'r') as zf:
            self.zip_entries = [info.filename for info in zf.infolist()]
            zf.extractall(self.extract_dir)

        # Hashear imagens originais
        media_dir = os.path.join(self.extract_dir, 'word', 'media')
        if os.path.isdir(media_dir):
            for fname in os.listdir(media_dir):
                fpath = os.path.join(media_dir, fname)
                with open(fpath, 'rb') as f:
                    self.media_hashes[fname] = hashlib.md5(f.read()).hexdigest()

        # Parse document.xml
        doc_xml = os.path.join(self.extract_dir, 'word', 'document.xml')
        self.tree = etree.parse(doc_xml)
        root = self.tree.getroot()
        self.body = root.find(f'{W}body')

    def _save(self, output_path):
        """Salva DOCX preservando ordem original do ZIP."""
        doc_xml = os.path.join(self.extract_dir, 'word', 'document.xml')
        self.tree.write(doc_xml, xml_declaration=True, encoding='UTF-8', standalone=True)

        if os.path.exists(output_path):
            os.remove(output_path)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
            # Primeiro, entradas na ordem original
            written = set()
            for entry in self.zip_entries:
                fpath = os.path.join(self.extract_dir, entry)
                if os.path.isfile(fpath):
                    zout.write(fpath, entry)
                    written.add(entry)
            # Depois, qualquer arquivo novo
            for root_dir, dirs, files in os.walk(self.extract_dir):
                for fname in files:
                    fpath = os.path.join(root_dir, fname)
                    arcname = os.path.relpath(fpath, self.extract_dir)
                    if arcname not in written:
                        zout.write(fpath, arcname)

    def _get_all_paras(self):
        """Retorna lista de todos os parágrafos do body."""
        return self.body.findall(f'{W}p')

    # =====================================================
    # FASE 0 — Recepção e detecção de duplicatas
    # =====================================================
    def phase0_analyze(self):
        """Analisa o documento: conta questões, detecta duplicatas."""
        self._extract()
        paras = self._get_all_paras()

        questions = []
        current_q = None

        for para in paras:
            text = get_para_text(para).strip()
            # Detectar início de questão (QUESTÃO N ou QUESTAO N)
            m = re.match(r'QUEST[AÃ]O\s+(\d+)', text, re.IGNORECASE)
            if m:
                if current_q:
                    questions.append(current_q)
                current_q = {
                    'number': int(m.group(1)),
                    'original_header': text,
                    'enunciado': '',
                    'alternativas': [],
                    'gabarito': '',
                    'categoria': '',
                    'has_highlight': False,
                    'has_resolucao_bold': False,
                    'has_referencias': False,
                    'ref_count': 0,
                    'has_grau': False,
                    'accent_issues': [],
                }
                continue

            if current_q is None:
                continue

            # Detectar categoria (geralmente logo após o header)
            if not current_q['categoria'] and not current_q['enunciado']:
                # Categoria é texto antes do enunciado que não começa com A-E)
                if text and not re.match(r'^[A-E]\)', text) and 'GABARITO' not in text:
                    if 'QUEST' not in text.upper() and text != current_q['original_header']:
                        # Provavelmente a categoria
                        if ' - ' in text or ' | ' in text or len(text) < 80:
                            current_q['categoria'] = text

            # Enunciado (texto substantivo antes das alternativas)
            if not re.match(r'^[A-E]\)', text) and 'GABARITO' not in text:
                if text and 'QUEST' not in text.upper() and '📖' not in text:
                    if text != current_q.get('categoria', ''):
                        current_q['enunciado'] += ' ' + text

            # Alternativas
            m_alt = re.match(r'^([A-E])\)\s*(.*)', text)
            if m_alt:
                current_q['alternativas'].append(text)
                # Checar highlight
                for run in para.findall(f'{W}r'):
                    rPr = run.find(f'{W}rPr')
                    if rPr is not None:
                        hl = rPr.find(f'{W}highlight')
                        if hl is not None and hl.get(f'{W}val') == 'yellow':
                            current_q['has_highlight'] = True

            # Gabarito
            m_gab = re.match(r'GABARITO:\s*([A-E])', text)
            if m_gab:
                current_q['gabarito'] = m_gab.group(1)

            # Resolução
            if '📖 Resolução' in text or '📖 Resolucao' in text:
                # Checar negrito
                for run in para.findall(f'{W}r'):
                    rPr = run.find(f'{W}rPr')
                    if rPr is not None and rPr.find(f'{W}b') is not None:
                        current_q['has_resolucao_bold'] = True

            # Referências
            if '📖 REFERÊNCIAS' in text or '📖 REFERENCIAS' in text:
                current_q['has_referencias'] = True

            # Contar bullets de referência
            if current_q['has_referencias'] and (text.startswith('•') or text.startswith('-')):
                current_q['ref_count'] += 1

            # Grau de dificuldade
            if '[GRAU DE DIFICULDADE]' in text:
                current_q['has_grau'] = True

            # Problemas de acentuação
            for wrong in ACCENT_FIXES:
                if wrong in text:
                    current_q['accent_issues'].append(wrong)

        if current_q:
            questions.append(current_q)

        self.questions = questions

        # Detectar duplicatas de conteúdo
        hashes = {}
        duplicates = []
        for q in questions:
            content = normalize_text(q['enunciado'] + ' '.join(q['alternativas']))
            h = hashlib.md5(content.encode()).hexdigest()
            if h in hashes:
                duplicates.append({
                    'q1': hashes[h]['number'],
                    'q2': q['number'],
                })
            else:
                hashes[h] = q

        # Detectar numeração repetida
        num_counts = {}
        for q in questions:
            n = q['number']
            num_counts[n] = num_counts.get(n, 0) + 1
        repeated_nums = [n for n, c in num_counts.items() if c > 1]

        return {
            'total_questions': len(questions),
            'questions': questions,
            'duplicates': duplicates,
            'repeated_numbers': repeated_nums,
            'media_files': len(self.media_hashes),
        }

    # =====================================================
    # FASE 1 — Auditoria estrutural
    # =====================================================
    def phase1_audit(self):
        """Gera relatório de auditoria estrutural."""
        issues = []
        for q in self.questions:
            q_issues = []
            if not q['has_grau']:
                q_issues.append('Sem [GRAU DE DIFICULDADE]')
            if not q['has_highlight']:
                q_issues.append('Sem highlight amarelo')
            if not q['has_resolucao_bold']:
                q_issues.append('📖 Resolução: sem negrito')
            if not q['has_referencias']:
                q_issues.append('Sem referência bibliográfica')
            if q['ref_count'] > 1:
                q_issues.append(f'{q["ref_count"]} referências (deve ter 1)')
            if q['accent_issues']:
                q_issues.append(f'Acentos: {", ".join(set(q["accent_issues"]))}')
            if q['categoria'] and ' | ' not in q['categoria'] and ' - ' not in q['categoria']:
                q_issues.append('Categoria sem subtema')
            if not q['gabarito']:
                q_issues.append('Sem GABARITO')

            issues.append({
                'number': q['number'],
                'header': q['original_header'],
                'categoria': q['categoria'],
                'issues': q_issues,
            })

        return {
            'issues': issues,
            'summary': {
                'sem_grau': sum(1 for i in issues if 'Sem [GRAU DE DIFICULDADE]' in i['issues']),
                'sem_highlight': sum(1 for i in issues if 'Sem highlight amarelo' in i['issues']),
                'sem_negrito_resolucao': sum(1 for i in issues if '📖 Resolução: sem negrito' in i['issues']),
                'sem_referencia': sum(1 for i in issues if 'Sem referência bibliográfica' in i['issues']),
                'refs_multiplas': sum(1 for i in issues if any('referências' in x for x in i['issues'])),
                'acentos': sum(1 for i in issues if any('Acentos' in x for x in i['issues'])),
                'sem_subtema': sum(1 for i in issues if 'Categoria sem subtema' in i['issues']),
            }
        }

    # =====================================================
    # FASE 4 — Aplicação dos ajustes (CORE)
    # =====================================================
    def phase4_process(self, config):
        """
        Aplica todos os ajustes sistemáticos.

        config: {
            'start_oqm': 1,           # Número inicial OQM
            'difficulties': {},        # {q_number: 'Fácil', ...}
            'categories': {},          # {q_number: 'Cat | Sub', ...}
        }
        """
        start_oqm = config.get('start_oqm', 1)
        difficulties = config.get('difficulties', {})
        categories = config.get('categories', {})
        # Flags de classificação
        apply_categories = config.get('apply_categories', True)
        apply_subtemas = config.get('apply_subtemas', True)
        apply_difficulties = config.get('apply_difficulties', True)
        # Flags de formatação
        apply_accents = config.get('apply_accents', True)
        apply_highlight = config.get('apply_highlight', True)
        apply_bold_resolucao = config.get('apply_bold_resolucao', True)
        apply_limit_refs = config.get('apply_limit_refs', True)
        # Flags de estrutura
        apply_insert_tags = config.get('apply_insert_tags', True)
        apply_video = config.get('apply_video', True)
        apply_remove_separators = config.get('apply_remove_separators', True)
        apply_page_breaks = config.get('apply_page_breaks', True)

        paras = self._get_all_paras()

        # ---- Passo 1: Mapear questões para parágrafos ----
        q_map = []  # Lista de { 'header_idx', 'number', 'paras_range': (start, end) }
        header_indices = []

        for i, para in enumerate(paras):
            text = get_para_text(para).strip()
            m = re.match(r'QUEST[AÃ]O\s+(\d+)', text, re.IGNORECASE)
            if m:
                header_indices.append((i, int(m.group(1))))

        for idx, (hi, qnum) in enumerate(header_indices):
            end = header_indices[idx + 1][0] if idx + 1 < len(header_indices) else len(paras)
            q_map.append({
                'header_idx': hi,
                'number': qnum,
                'end_idx': end,
            })

        # ---- Passo 4.1: Correção global de acentos ----
        if apply_accents:
            for para in paras:
                fix_accents_in_para(para)

        # ---- Passo 4.3: IDs OQM ----
        for seq, qm in enumerate(q_map):
            oqm_id = f'OQM{start_oqm + seq:05d}'
            para = paras[qm['header_idx']]
            # Substituir texto do header (preservando formatação do 1º run)
            set_para_text_preserve_format(para, oqm_id)
            # Remover qualquer pageBreakBefore existente no header OQM
            remove_page_break_before(para)
            qm['oqm_id'] = oqm_id

        # ---- Passo 4.4: Reformatação de categoria (" - " → " | ") ----
        # apply_categories controla a parte antes do " | " (Categoria principal)
        # apply_subtemas controla a parte depois do " | " (Subtema)
        for qm in q_map:
            start = qm['header_idx'] + 1
            end = min(qm['header_idx'] + 5, qm['end_idx'])  # Categoria está próxima do header
            for i in range(start, end):
                para = paras[i]
                text = get_para_text(para).strip()
                if not text or re.match(r'^[A-E]\)', text) or 'GABARITO' in text:
                    continue
                if 'QUEST' in text.upper() or '📖' in text or '[' in text:
                    continue
                # Provável categoria
                if ' - ' in text:
                    # Substituir apenas a 1ª ocorrência de " - " por " | "
                    new_text = text.replace(' - ', ' | ', 1)
                    # Se temos categoria override do config, aplicar conforme flags
                    qnum = qm['number']
                    if qnum in categories and (apply_categories or apply_subtemas):
                        override = categories[qnum]
                        # Separar categoria e subtema do override
                        if ' | ' in override:
                            cat_part, sub_part = override.split(' | ', 1)
                        else:
                            cat_part, sub_part = override, ''
                        # Separar categoria e subtema do texto atual
                        if ' | ' in new_text:
                            orig_cat, orig_sub = new_text.split(' | ', 1)
                        else:
                            orig_cat, orig_sub = new_text, ''
                        # Aplicar apenas as partes habilitadas
                        final_cat = cat_part if apply_categories else orig_cat
                        final_sub = sub_part if apply_subtemas else orig_sub
                        new_text = f'{final_cat} | {final_sub}' if final_sub else final_cat

                    set_para_text_preserve_format(para, new_text)
                    qm['categoria_para_idx'] = i
                    break
                elif ' | ' in text:
                    # Já no formato correto, mas pode ter override
                    qnum = qm['number']
                    if qnum in categories and (apply_categories or apply_subtemas):
                        override = categories[qnum]
                        if ' | ' in override:
                            cat_part, sub_part = override.split(' | ', 1)
                        else:
                            cat_part, sub_part = override, ''
                        orig_cat, orig_sub = text.split(' | ', 1)
                        final_cat = cat_part if apply_categories else orig_cat
                        final_sub = sub_part if apply_subtemas else orig_sub
                        new_text = f'{final_cat} | {final_sub}' if final_sub else final_cat
                        set_para_text_preserve_format(para, new_text)
                    qm['categoria_para_idx'] = i
                    break
                elif len(text) < 80 and not re.match(r'^\d', text):
                    # Categoria sem subtema
                    qnum = qm['number']
                    if qnum in categories and (apply_categories or apply_subtemas):
                        override = categories[qnum]
                        if ' | ' in override:
                            cat_part, sub_part = override.split(' | ', 1)
                        else:
                            cat_part, sub_part = override, ''
                        final_cat = cat_part if apply_categories else text
                        final_sub = sub_part if apply_subtemas else ''
                        new_text = f'{final_cat} | {final_sub}' if final_sub else final_cat
                        set_para_text_preserve_format(para, new_text)
                    qm['categoria_para_idx'] = i
                    break

        # ---- Passo 4.5: Highlight amarelo na alternativa correta ----
        if apply_highlight:
            paras = self._get_all_paras()
            gabaritos = {}
            current_qnum = None
            for para in paras:
                text = get_para_text(para).strip()
                if re.match(r'OQM\d{5}', text):
                    for qm in q_map:
                        if qm.get('oqm_id') == text:
                            current_qnum = qm['number']
                            break
                m = re.match(r'QUEST[AÃ]O\s+(\d+)', text, re.IGNORECASE)
                if m:
                    current_qnum = int(m.group(1))
                m_gab = re.match(r'GABARITO:\s*([A-E])', text)
                if m_gab and current_qnum:
                    gabaritos[current_qnum] = m_gab.group(1)

            current_qnum = None
            for para in paras:
                text = get_para_text(para).strip()
                if re.match(r'OQM\d{5}', text):
                    for qm in q_map:
                        if qm.get('oqm_id') == text:
                            current_qnum = qm['number']
                            break
                m = re.match(r'QUEST[AÃ]O\s+(\d+)', text, re.IGNORECASE)
                if m:
                    current_qnum = int(m.group(1))
                m_alt = re.match(r'^([A-E])\)', text)
                if m_alt and current_qnum:
                    letra = m_alt.group(1)
                    gab = gabaritos.get(current_qnum, '')
                    if letra == gab:
                        set_highlight_yellow(para)
                    else:
                        remove_highlight(para)

        # ---- Passo 4.6: Remoção de referências extras ----
        if apply_limit_refs:
            paras = self._get_all_paras()
            in_refs = False
            ref_bullet_count = 0
            to_remove = []

            for para in paras:
                text = get_para_text(para).strip()
                if '📖 REFERÊNCIAS' in text or '📖 REFERENCIAS' in text:
                    in_refs = True
                    ref_bullet_count = 0
                    continue
                if in_refs:
                    if re.match(r'QUEST[AÃ]O\s+\d+', text, re.IGNORECASE) or re.match(r'OQM\d{5}', text):
                        in_refs = False
                        ref_bullet_count = 0
                        continue
                    if is_underscore_separator(text):
                        in_refs = False
                        ref_bullet_count = 0
                        continue
                    if '[NOME DA QUESTÃO]' in text:
                        in_refs = False
                        ref_bullet_count = 0
                        continue
                    if text.startswith('•') or text.startswith('-') or text.startswith('–'):
                        ref_bullet_count += 1
                        if ref_bullet_count > 1:
                            to_remove.append(para)

            for para in to_remove:
                if para.getparent() is not None:
                    para.getparent().remove(para)

        # ---- Passo 4.7: Negrito em "📖 Resolução:" ----
        if apply_bold_resolucao:
            paras = self._get_all_paras()
            for para in paras:
                text = get_para_text(para).strip()
                if '📖 Resolução' in text or '📖 Resolucao' in text:
                    set_bold(para)

        # ---- Passo 4.10 (antecipado): Remover separadores de underscores ----
        if apply_remove_separators:
            paras = self._get_all_paras()
            to_remove = []
            for para in paras:
                text = get_para_text(para).strip()
                if is_underscore_separator(text):
                    to_remove.append(para)
            for para in to_remove:
                if para.getparent() is not None:
                    para.getparent().remove(para)

        # ---- Passo 4.10b: Remover <w:br w:type="page"/> isolados ----
        paras = self._get_all_paras()
        to_remove = []
        for para in paras:
            text = get_para_text(para).strip()
            has_br = False
            for run in para.findall(f'{W}r'):
                for br in run.findall(f'{W}br'):
                    if br.get(f'{W}type') == 'page':
                        has_br = True
            if has_br and not text:
                to_remove.append(para)
            elif has_br:
                remove_br_page(para)
        for para in to_remove:
            if para.getparent() is not None:
                para.getparent().remove(para)

        # ---- Passo 4.8 + 4.9 + 4.11 + 4.12: Inserir tags, vídeo, pageBreaks, linhas em branco ----
        # Trabalhar de trás para frente para preservar índices
        paras = self._get_all_paras()

        # Re-mapear questões nos parágrafos atuais
        q_positions = []  # Lista de dicts com índices relevantes de cada questão
        current_q = None

        for i, para in enumerate(paras):
            text = get_para_text(para).strip()

            # Header OQM
            if re.match(r'OQM\d{5}', text):
                if current_q:
                    current_q['end_idx'] = i
                    q_positions.append(current_q)
                oqm_id = text
                qm = next((q for q in q_map if q.get('oqm_id') == oqm_id), None)
                current_q = {
                    'oqm_id': oqm_id,
                    'number': qm['number'] if qm else 0,
                    'header_idx': i,
                    'cat_idx': None,
                    'first_alt_idx': None,
                    'gabarito_idx': None,
                    'enunciado_start_idx': None,
                    'resolucao_idx': None,
                    'refs_idx': None,
                    'last_ref_bullet_idx': None,
                    'end_idx': len(paras),
                }
                continue

            if current_q is None:
                continue

            # Categoria (1-3 linhas após header)
            if current_q['cat_idx'] is None and i <= current_q['header_idx'] + 4:
                if text and not re.match(r'^[A-E]\)', text) and 'GABARITO' not in text:
                    if '📖' not in text and '[' not in text and 'OQM' not in text:
                        if len(text) < 120:
                            current_q['cat_idx'] = i

            # Primeira alternativa
            if current_q['first_alt_idx'] is None and re.match(r'^[A-E]\)', text):
                current_q['first_alt_idx'] = i

            # Enunciado: primeiro parágrafo substancial entre categoria e alternativa A
            if (current_q['enunciado_start_idx'] is None and
                current_q['cat_idx'] is not None and
                i > current_q['cat_idx'] and
                current_q['first_alt_idx'] is None):
                if text and len(text) > 10:
                    current_q['enunciado_start_idx'] = i

            # GABARITO
            if re.match(r'GABARITO:\s*[A-E]', text):
                current_q['gabarito_idx'] = i

            # 📖 Resolução
            if '📖 Resolução' in text:
                current_q['resolucao_idx'] = i

            # 📖 REFERÊNCIAS
            if '📖 REFERÊNCIAS' in text:
                current_q['refs_idx'] = i

            # Último bullet de referência
            if current_q['refs_idx'] is not None and (text.startswith('•') or text.startswith('-') or text.startswith('–')):
                current_q['last_ref_bullet_idx'] = i

        if current_q:
            current_q['end_idx'] = len(paras)
            q_positions.append(current_q)

        # Inserir de trás para frente
        for qi, qpos in enumerate(reversed(q_positions)):
            real_idx = len(q_positions) - 1 - qi
            paras = self._get_all_paras()

            # Re-encontrar posições (porque inserções anteriores mudaram índices)
            oqm_id = qpos['oqm_id']
            header_idx = None
            cat_idx = None
            first_alt_idx = None
            gabarito_idx = None
            enunciado_start_idx = None
            refs_idx = None
            last_ref_bullet_idx = None

            for i, para in enumerate(paras):
                text = get_para_text(para).strip()
                if text == oqm_id:
                    header_idx = i
                    continue
                if header_idx is not None and cat_idx is None and i <= header_idx + 4:
                    if text and not re.match(r'^[A-E]\)', text) and 'GABARITO' not in text:
                        if '📖' not in text and '[' not in text and 'OQM' not in text:
                            if len(text) < 120:
                                cat_idx = i
                if header_idx is not None and first_alt_idx is None and re.match(r'^[A-E]\)', text):
                    first_alt_idx = i
                if header_idx is not None and enunciado_start_idx is None:
                    if cat_idx is not None and i > cat_idx and first_alt_idx is None:
                        if text and len(text) > 10 and not re.match(r'^[A-E]\)', text):
                            enunciado_start_idx = i
                if header_idx is not None and re.match(r'GABARITO:\s*[A-E]', text):
                    gabarito_idx = i
                if header_idx is not None and '📖 REFERÊNCIAS' in text:
                    refs_idx = i
                if refs_idx is not None and (text.startswith('•') or text.startswith('-') or text.startswith('–')):
                    last_ref_bullet_idx = i

                # Parar quando chegar à próxima questão
                if header_idx is not None and i > header_idx + 2:
                    if re.match(r'OQM\d{5}', text) and text != oqm_id:
                        break

            if header_idx is None:
                continue

            # --- Inserir [VÍDEO] + URL após último bullet de referência ---
            if apply_video:
                insert_after = last_ref_bullet_idx or refs_idx
                if insert_after is not None:
                    paras = self._get_all_paras()
                    found_bullet = False
                    for i, p in enumerate(paras):
                        t = get_para_text(p).strip()
                        if (t.startswith('•') or t.startswith('-') or t.startswith('–')) and i >= (refs_idx or 0):
                            # Checar se é o último bullet
                            next_is_bullet = False
                            if i + 1 < len(paras):
                                nt = get_para_text(paras[i + 1]).strip()
                                if nt.startswith('•') or nt.startswith('-') or nt.startswith('–'):
                                    next_is_bullet = True
                            if not next_is_bullet:
                                # Este é o último bullet
                                p.addnext(make_text_para(VIDEO_URL, underline=True))
                                p.addnext(make_tag_para('[VÍDEO]'))
                                p.addnext(make_empty_para())
                                found_bullet = True
                                break
                    if not found_bullet and refs_idx is not None:
                        ref_p = paras[refs_idx]
                        ref_p.addnext(make_text_para(VIDEO_URL, underline=True))
                        ref_p.addnext(make_tag_para('[VÍDEO]'))
                        ref_p.addnext(make_empty_para())

            # --- Re-obter parágrafos ---
            paras = self._get_all_paras()

            # Re-encontrar posições
            header_idx = None
            cat_idx = None
            first_alt_idx = None
            gabarito_idx = None
            enunciado_start_idx = None

            for i, para in enumerate(paras):
                text = get_para_text(para).strip()
                if text == oqm_id:
                    header_idx = i
                    continue
                if header_idx is not None and cat_idx is None and i <= header_idx + 4:
                    if text and not re.match(r'^[A-E]\)', text) and 'GABARITO' not in text:
                        if '📖' not in text and '[' not in text and 'OQM' not in text:
                            if len(text) < 120:
                                cat_idx = i
                if header_idx is not None and first_alt_idx is None and re.match(r'^[A-E]\)', text):
                    first_alt_idx = i
                if header_idx is not None and enunciado_start_idx is None:
                    if cat_idx is not None and i > cat_idx and first_alt_idx is None:
                        if text and len(text) > 10:
                            enunciado_start_idx = i
                if header_idx is not None and re.match(r'GABARITO:\s*[A-E]', text):
                    gabarito_idx = i
                if header_idx is not None and i > header_idx + 2:
                    if re.match(r'OQM\d{5}', text) and text != oqm_id:
                        break

            if header_idx is None:
                continue

            # --- Inserir tags estruturais (condicionado por apply_insert_tags) ---
            if apply_insert_tags:
                # --- Inserir [COMENTÁRIOS] antes de GABARITO ---
                if gabarito_idx is not None:
                    gab_para = paras[gabarito_idx]
                    gab_para.addprevious(make_tag_para('[COMENTÁRIOS]'))
                    gab_para.addprevious(make_empty_para())

                # --- Inserir [ALTERNATIVAS...] antes da 1ª alternativa ---
                paras = self._get_all_paras()
                for i, p in enumerate(paras):
                    text = get_para_text(p).strip()
                    if text == oqm_id:
                        for j in range(i + 1, min(i + 30, len(paras))):
                            t2 = get_para_text(paras[j]).strip()
                            if re.match(r'^A\)', t2):
                                paras[j].addprevious(make_empty_para())
                                paras[j].addprevious(make_tag_para('[ALTERNATIVAS, SENDO A ALTERNATIVA PINTADA DE AMARELO A CORRETA]'))
                                break
                            if re.match(r'OQM\d{5}', t2) and t2 != oqm_id:
                                break
                        break

                # --- Inserir [ENUNCIADO] antes do enunciado ---
                paras = self._get_all_paras()
                for i, p in enumerate(paras):
                    text = get_para_text(p).strip()
                    if text == oqm_id:
                        found_cat = False
                        for j in range(i + 1, min(i + 20, len(paras))):
                            t2 = get_para_text(paras[j]).strip()
                            if not found_cat and t2 and len(t2) < 120 and not re.match(r'^[A-E]\)', t2):
                                if '📖' not in t2 and '[' not in t2 and 'OQM' not in t2 and 'GABARITO' not in t2:
                                    found_cat = True
                                    continue
                            if found_cat and t2 and not re.match(r'^\[', t2):
                                if t2 and 'ALTERNATIVA' not in t2:
                                    paras[j].addprevious(make_empty_para())
                                    paras[j].addprevious(make_tag_para('[ENUNCIADO]'))
                                    break
                        break

            # --- Inserir [GRAU DE DIFICULDADE] + grau após categoria ---
            if apply_difficulties:
                paras = self._get_all_paras()
                difficulty = difficulties.get(qpos['number'], 'Mediano')
                for i, p in enumerate(paras):
                    text = get_para_text(p).strip()
                    if text == oqm_id:
                        for j in range(i + 1, min(i + 10, len(paras))):
                            t2 = get_para_text(paras[j]).strip()
                            if t2 and len(t2) < 120 and not re.match(r'^[A-E]\)', t2):
                                if '📖' not in t2 and '[' not in t2 and 'OQM' not in t2:
                                    # Esta é a categoria — inserir grau DEPOIS dela
                                    paras[j].addnext(make_text_para(difficulty))
                                    paras[j].addnext(make_tag_para('[GRAU DE DIFICULDADE]'))
                                    paras[j].addnext(make_empty_para())
                                    break
                        break

            if apply_insert_tags:
                # --- Inserir [CATEGORIA | SUBTEMA] antes da categoria ---
                paras = self._get_all_paras()
                for i, p in enumerate(paras):
                    text = get_para_text(p).strip()
                    if text == oqm_id:
                        for j in range(i + 1, min(i + 5, len(paras))):
                            t2 = get_para_text(paras[j]).strip()
                            if t2 and len(t2) < 120 and not re.match(r'^[A-E]\)', t2):
                                if '📖' not in t2 and '[' not in t2 and 'OQM' not in t2:
                                    paras[j].addprevious(make_empty_para())
                                    paras[j].addprevious(make_tag_para('[CATEGORIA | SUBTEMA]'))
                                    break
                        break

                # --- Inserir [NOME DA QUESTÃO] antes do header OQM ---
                paras = self._get_all_paras()
                is_first = (real_idx == 0)
                use_page_break = apply_page_breaks and not is_first
                for i, p in enumerate(paras):
                    text = get_para_text(p).strip()
                    if text == oqm_id:
                        paras[i].addprevious(make_tag_para('[NOME DA QUESTÃO]', page_break=use_page_break))
                        break

        # ---- Passo 4.10: Formatação visual das tags ----
        paras = self._get_all_paras()
        for para in paras:
            text = get_para_text(para).strip()
            if text in REQUIRED_TAGS:
                set_color_gray(para)
                remove_bold(para)

        # ---- Passo 4.12: Garantir linhas em branco antes de 📖 REFERÊNCIAS ----
        paras = self._get_all_paras()
        for i, para in enumerate(paras):
            text = get_para_text(para).strip()
            if '📖 REFERÊNCIAS' in text:
                # Verificar se já tem linha em branco antes
                if i > 0:
                    prev_text = get_para_text(paras[i - 1]).strip()
                    if prev_text:  # Não é vazio
                        para.addprevious(make_empty_para())

    # =====================================================
    # FASE 5 — Validação automática
    # =====================================================
    def phase5_validate(self):
        """Executa 14 critérios de validação."""
        paras = self._get_all_paras()
        results = []

        # Reconstruir mapa de questões
        q_validations = []
        current_q = None
        pending_nome_tag = None  # [NOME DA QUESTÃO] aparece ANTES do OQM header

        for i, para in enumerate(paras):
            text = get_para_text(para).strip()

            # [NOME DA QUESTÃO] aparece antes do OQM header — guardar para a próxima questão
            if '[NOME DA QUESTÃO]' in text:
                pending_nome_tag = {
                    'para': para,
                    'has_gray': False,
                    'has_bold': False,
                    'has_page_break': False,
                }
                for run in para.findall(f'{W}r'):
                    rPr = run.find(f'{W}rPr')
                    if rPr is not None:
                        c = rPr.find(f'{W}color')
                        if c is not None and c.get(f'{W}val') == '808080':
                            pending_nome_tag['has_gray'] = True
                        if rPr.find(f'{W}b') is not None:
                            pending_nome_tag['has_bold'] = True
                pPr = para.find(f'{W}pPr')
                if pPr is not None and pPr.find(f'{W}pageBreakBefore') is not None:
                    pending_nome_tag['has_page_break'] = True
                continue

            if re.match(r'OQM\d{5}', text):
                if current_q:
                    q_validations.append(current_q)
                current_q = {
                    'oqm_id': text,
                    'tags_found': [],
                    'tags_order_ok': True,
                    'gabarito': '',
                    'highlight_letter': None,
                    'highlight_count': 0,
                    'resolucao_bold': False,
                    'refs_bold': False,
                    'ref_bullet_count': 0,
                    'has_video_url': False,
                    'cat_has_pipe': False,
                    'difficulty_valid': False,
                    'page_break_before_nome': False,
                    'page_break_before_oqm': False,
                    'issues': [],
                }
                # Incorporar [NOME DA QUESTÃO] pendente
                if pending_nome_tag:
                    current_q['tags_found'].append('[NOME DA QUESTÃO]')
                    current_q['page_break_before_nome'] = pending_nome_tag['has_page_break']
                    if not pending_nome_tag['has_gray']:
                        current_q['issues'].append('[NOME DA QUESTÃO] sem cor cinza')
                    if pending_nome_tag['has_bold']:
                        current_q['issues'].append('[NOME DA QUESTÃO] com negrito indevido')
                    pending_nome_tag = None
                # Checar pageBreakBefore no OQM header
                pPr = para.find(f'{W}pPr')
                if pPr is not None and pPr.find(f'{W}pageBreakBefore') is not None:
                    current_q['page_break_before_oqm'] = True
                continue

            if current_q is None:
                continue

            # Tags (exceto [NOME DA QUESTÃO] que já foi tratado acima)
            for tag in REQUIRED_TAGS:
                if tag == '[NOME DA QUESTÃO]':
                    continue  # Já tratado via pending_nome_tag
                if tag in text:
                    current_q['tags_found'].append(tag)
                    # Checar cor cinza e sem negrito
                    has_gray = False
                    has_bold = False
                    for run in para.findall(f'{W}r'):
                        rPr = run.find(f'{W}rPr')
                        if rPr is not None:
                            c = rPr.find(f'{W}color')
                            if c is not None and c.get(f'{W}val') == '808080':
                                has_gray = True
                            if rPr.find(f'{W}b') is not None:
                                has_bold = True
                    if not has_gray:
                        current_q['issues'].append(f'{tag} sem cor cinza')
                    if has_bold:
                        current_q['issues'].append(f'{tag} com negrito indevido')

                    # Checar pageBreakBefore em [NOME DA QUESTÃO]
                    if tag == '[NOME DA QUESTÃO]':
                        pPr = para.find(f'{W}pPr')
                        if pPr is not None and pPr.find(f'{W}pageBreakBefore') is not None:
                            current_q['page_break_before_nome'] = True

            # Gabarito
            m = re.match(r'GABARITO:\s*([A-E])', text)
            if m:
                current_q['gabarito'] = m.group(1)

            # Highlight
            m_alt = re.match(r'^([A-E])\)', text)
            if m_alt:
                for run in para.findall(f'{W}r'):
                    rPr = run.find(f'{W}rPr')
                    if rPr is not None:
                        hl = rPr.find(f'{W}highlight')
                        if hl is not None and hl.get(f'{W}val') == 'yellow':
                            current_q['highlight_count'] += 1
                            current_q['highlight_letter'] = m_alt.group(1)
                            break

            # 📖 Resolução: bold
            if '📖 Resolução' in text:
                for run in para.findall(f'{W}r'):
                    rPr = run.find(f'{W}rPr')
                    if rPr is not None and rPr.find(f'{W}b') is not None:
                        current_q['resolucao_bold'] = True

            # 📖 REFERÊNCIAS: bold + count bullets
            if '📖 REFERÊNCIAS' in text:
                for run in para.findall(f'{W}r'):
                    rPr = run.find(f'{W}rPr')
                    if rPr is not None and rPr.find(f'{W}b') is not None:
                        current_q['refs_bold'] = True

            if current_q.get('refs_bold') is not None and (text.startswith('•') or text.startswith('-') or text.startswith('–')):
                current_q['ref_bullet_count'] += 1

            # URL vídeo
            if VIDEO_URL in text:
                current_q['has_video_url'] = True

            # Categoria com pipe
            if '[CATEGORIA | SUBTEMA]' in get_para_text(paras[i - 1] if i > 0 else para).strip() if i > 0 else False:
                if ' | ' in text:
                    current_q['cat_has_pipe'] = True

            # Dificuldade válida
            if text in VALID_DIFFICULTIES:
                current_q['difficulty_valid'] = True

        if current_q:
            q_validations.append(current_q)

        # Compilar resultados
        total = len(q_validations)
        all_ok = True

        # Checar IDs sequenciais
        oqm_ids = [q['oqm_id'] for q in q_validations]
        ids_sequential = True
        for i in range(1, len(oqm_ids)):
            curr_num = int(oqm_ids[i][3:])
            prev_num = int(oqm_ids[i - 1][3:])
            if curr_num != prev_num + 1:
                ids_sequential = False
                break

        validation = {
            'total': total,
            'ids_sequential': ids_sequential,
            'questions': [],
        }

        for i, q in enumerate(q_validations):
            q_result = {
                'oqm_id': q['oqm_id'],
                'checks': {
                    'all_tags': len(q['tags_found']) == 7,
                    'tags_order': q['tags_found'] == [t for t in REQUIRED_TAGS if t in q['tags_found']],
                    'gabarito_valid': bool(re.match(r'^[A-E]$', q['gabarito'])),
                    'highlight_correct': q['highlight_count'] == 1 and q['highlight_letter'] == q['gabarito'],
                    'resolucao_bold': q['resolucao_bold'],
                    'ref_1_bullet': q['ref_bullet_count'] == 1,
                    'has_video': q['has_video_url'],
                    'difficulty_valid': q['difficulty_valid'],
                    'page_break_nome': q['page_break_before_nome'] if i > 0 else True,
                    'no_page_break_oqm': not q['page_break_before_oqm'],
                },
                'issues': q['issues'],
            }
            validation['questions'].append(q_result)

        # Verificar imagens
        media_dir = os.path.join(self.extract_dir, 'word', 'media')
        images_ok = True
        if os.path.isdir(media_dir):
            for fname in os.listdir(media_dir):
                fpath = os.path.join(media_dir, fname)
                with open(fpath, 'rb') as f:
                    current_hash = hashlib.md5(f.read()).hexdigest()
                if fname in self.media_hashes:
                    if current_hash != self.media_hashes[fname]:
                        images_ok = False
                        break
        validation['images_preserved'] = images_ok

        return validation

    # =====================================================
    # MÉTODO PRINCIPAL — Processar tudo
    # =====================================================
    def process(self, output_path, config):
        """
        Executa o pipeline completo: análise → processamento → validação → salvar.

        config: {
            'start_oqm': 1,
            'difficulties': {1: 'Fácil', 2: 'Mediano', ...},
            'categories': {1: 'Joelho | Vias de Acesso', ...},
            'apply_categories': True,
            'apply_subtemas': True,
            'apply_difficulties': True,
            'apply_video': True,
        }

        Retorna: { 'analysis', 'audit', 'validation' }
        """
        # Fase 0
        analysis = self.phase0_analyze()

        # Fase 1
        audit = self.phase1_audit()

        # Fase 4
        self.phase4_process(config)

        # Fase 5
        validation = self.phase5_validate()

        # Ajustar validação: se flags desabilitadas, não penalizar checks correspondentes
        for q in validation.get('questions', []):
            checks = q.get('checks', {})
            if not config.get('apply_difficulties', True):
                checks['difficulty_valid'] = True
            if not config.get('apply_video', True):
                checks['has_video'] = True
            if not config.get('apply_insert_tags', True):
                checks['all_tags'] = True
                checks['tags_order'] = True
            if not config.get('apply_highlight', True):
                checks['highlight_correct'] = True
            if not config.get('apply_bold_resolucao', True):
                checks['resolucao_bold'] = True
            if not config.get('apply_limit_refs', True):
                checks['ref_1_bullet'] = True
            if not config.get('apply_page_breaks', True):
                checks['page_break_nome'] = True

        # Salvar
        self._save(output_path)

        return {
            'analysis': analysis,
            'audit': audit,
            'validation': validation,
        }

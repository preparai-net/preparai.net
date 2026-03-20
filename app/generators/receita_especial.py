"""
Gerador de Receita Especial — Manipulação XML do template TEMPLATE_RECEITA_ESPECIAL.docx
Máximo 2 medicamentos por receita. Paisagem, duas vias lado a lado.
"""
import os
import shutil
import re
from app.utils.unpack import unpack_docx
from app.utils.pack import pack_docx

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '..', 'templates', 'TEMPLATE_RECEITA_ESPECIAL.docx')


def gerar_receita_especial(
    output_path: str,
    nome_paciente: str,
    data: str,
    medicamento1_nome: str,
    medicamento1_posologia: str,
    medicamento1_qtd: str,
    medicamento2_nome: str = "",
    medicamento2_posologia: str = "",
    medicamento2_qtd: str = "",
    temp_dir: str = "/tmp"
):
    """
    Gera uma receita especial com 1 ou 2 medicamentos.
    Se medicamento2 estiver vazio, o slot 2 fica vazio.
    """
    work_dir = os.path.join(temp_dir, f'recesp_{os.getpid()}_{id(output_path)}')
    unpack_dir = os.path.join(work_dir, 'unpacked')

    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    temp_docx = os.path.join(work_dir, 'template.docx')
    shutil.copy2(TEMPLATE_PATH, temp_docx)

    unpack_docx(temp_docx, unpack_dir)

    # Formatar linhas de medicamento
    linha_med1 = f"1. {medicamento1_nome} ------------------------------------- {medicamento1_qtd}" if medicamento1_nome else ""
    linha_med2 = f"2. {medicamento2_nome} ------------------------------------- {medicamento2_qtd}" if medicamento2_nome else ""

    # === core.xml ===
    core_path = os.path.join(unpack_dir, 'docProps', 'core.xml')
    if os.path.exists(core_path):
        core = _read_file(core_path)
        # dc:subject → NOME DO PACIENTE (aparece em 4 SDTs)
        core = _replace_tag_content(core, 'dc:subject', nome_paciente)
        # dc:creator → MEDICAMENTO 1
        core = _replace_tag_content(core, 'dc:creator', linha_med1)
        # cp:contentStatus → MEDICAMENTO 2
        core = _replace_tag_content(core, 'cp:contentStatus', linha_med2)
        _write_file(core_path, core)

    # === app.xml ===
    app_path = os.path.join(unpack_dir, 'docProps', 'app.xml')
    if os.path.exists(app_path):
        app = _read_file(app_path)
        # Company → POSOLOGIA MEDICAMENTO 1
        app = _replace_tag_content(app, 'Company', medicamento1_posologia)
        _write_file(app_path, app)

    # === customXml/item1.xml ===
    item1_path = os.path.join(unpack_dir, 'customXml', 'item1.xml')
    if os.path.exists(item1_path):
        item1 = _read_file(item1_path)
        # CompanyFax → POSOLOGIA MEDICAMENTO 2
        item1 = _replace_tag_content(item1, 'CompanyFax', medicamento2_posologia)
        _write_file(item1_path, item1)

    # === document.xml — Substituir conteúdo dos SDTs diretamente ===
    doc_path = os.path.join(unpack_dir, 'word', 'document.xml')
    if os.path.exists(doc_path):
        doc = _read_file(doc_path)

        # Substituir nome do paciente em texto não-SDT
        doc = doc.replace('NOME DO PACIENTE', nome_paciente)

        # Substituir data
        doc = re.sub(r'\d{2}/\d{2}/\d{4}', data, doc)

        # === Substituir conteúdo dos SDTs ===
        # Os SDTs têm bindings via xpath. LibreOffice NÃO atualiza o cached content
        # a partir das propriedades, então precisamos substituir diretamente.

        # Mapeamento: xpath → texto de substituição
        # IMPORTANTE: Chaves mais específicas PRIMEIRO (CompanyFax antes de Company)
        # para evitar match parcial
        sdt_replacements = [
            ('creator', linha_med1),           # dc:creator → med1
            ('contentStatus', linha_med2),     # cp:contentStatus → med2
            ('CompanyFax', medicamento2_posologia),  # CompanyFax → pos2
            ('Company', medicamento1_posologia),     # Company → pos1 (mais genérico por último)
        ]

        doc = _replace_sdt_contents(doc, sdt_replacements)

        _write_file(doc_path, doc)

    # Reempacotar
    pack_docx(unpack_dir, output_path)

    # Limpar
    shutil.rmtree(work_dir, ignore_errors=True)

    return output_path


def _replace_sdt_contents(xml_str, replacements):
    """
    Encontra todos os SDTs no XML e substitui o conteúdo com base no xpath binding.
    replacements: lista de tuplas [(key, text), ...] — ordem importa (mais específico primeiro)
    """
    def sdt_replacer(match):
        full_sdt = match.group(0)
        sdt_inner = match.group(1)

        # Determinar qual binding este SDT usa (primeiro match ganha)
        replacement_text = None
        for key, text in replacements:
            if key in sdt_inner:
                replacement_text = text
                break

        if replacement_text is None:
            return full_sdt  # Não modificar SDTs que não reconhecemos

        # Encontrar o sdtContent e substituir seus runs com texto novo
        sdt_content_match = re.search(
            r'(<w:sdtContent>)(.*?)(</w:sdtContent>)',
            full_sdt,
            re.DOTALL
        )
        if not sdt_content_match:
            return full_sdt

        old_content = sdt_content_match.group(2)

        # Extrair o rPr (formatação) do primeiro run para preservar
        rpr_match = re.search(r'(<w:rPr>.*?</w:rPr>)', old_content, re.DOTALL)
        rpr = rpr_match.group(1) if rpr_match else ''

        # Extrair o pPr (formatação do parágrafo) se existir
        ppr_match = re.search(r'(<w:pPr>.*?</w:pPr>)', old_content, re.DOTALL)
        ppr = ppr_match.group(1) if ppr_match else ''

        # Extrair o paraId do parágrafo se existir
        p_attrs_match = re.search(r'<w:p ([^>]+)>', old_content)
        p_attrs = p_attrs_match.group(1) if p_attrs_match else ''

        # Construir novo conteúdo com um único run
        if replacement_text:
            escaped_text = _escape_xml(replacement_text)
            new_run = f'<w:r>{rpr}<w:t xml:space="preserve">{escaped_text}</w:t></w:r>'
        else:
            new_run = ''

        new_content = f'<w:p {p_attrs}>{ppr}{new_run}</w:p>'
        new_sdt_content = sdt_content_match.group(1) + new_content + sdt_content_match.group(3)

        # Substituir sdtContent no SDT completo
        result = full_sdt[:sdt_content_match.start()] + new_sdt_content + full_sdt[sdt_content_match.end():]
        return result

    # Aplicar em todos os SDTs
    return re.sub(r'<w:sdt>(.*?)</w:sdt>', sdt_replacer, xml_str, flags=re.DOTALL)


def _escape_xml(text):
    """Escapa caracteres especiais para XML."""
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


def _replace_tag_content(xml_str, tag_name, new_value):
    """Substitui o conteúdo de uma tag XML pelo novo valor."""
    pattern = re.compile(
        rf'(<{tag_name}[^>]*>)(.*?)(</{tag_name}>)',
        re.DOTALL
    )
    result = pattern.sub(rf'\g<1>{_escape_for_sub(new_value)}\g<3>', xml_str, count=1)
    return result


def _escape_for_sub(text):
    """Escapa caracteres especiais para re.sub."""
    return text.replace('\\', '\\\\').replace('\n', ' ')


def _read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

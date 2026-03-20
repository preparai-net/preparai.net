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

    # === document.xml ===
    doc_path = os.path.join(unpack_dir, 'word', 'document.xml')
    if os.path.exists(doc_path):
        doc = _read_file(doc_path)

        # Substituir nome do paciente
        doc = doc.replace('NOME DO PACIENTE', nome_paciente)

        # Substituir data
        doc = re.sub(r'\d{2}/\d{2}/\d{4}', data, doc)

        # Substituir textos de exemplo dos medicamentos no document.xml
        # O template tem "1. EXEMPLO ---... CX" e "2. EXEMPLO ---... CX" em cada via
        # Quando há 2 medicamentos: substituir o 1o pelo med1, o 2o pelo med2
        # Quando há 1 medicamento: substituir o 1o pelo med1, LIMPAR o 2o

        # Contador para saber qual ocorrência estamos (alterna entre med1 e med2)
        _replace_counter = [0]

        def _replace_exemplo(match):
            _replace_counter[0] += 1
            # Ocorrências ímpares (1a, 3a) = med1 | Pares (2a, 4a) = med2
            if _replace_counter[0] % 2 == 1:
                # Slot medicamento 1
                if medicamento1_nome:
                    return f'{medicamento1_nome} ------------------------------------- {medicamento1_qtd}'
                return ''
            else:
                # Slot medicamento 2
                if medicamento2_nome:
                    return f'{medicamento2_nome} ------------------------------------- {medicamento2_qtd}'
                return ''

        doc = re.sub(r'EXEMPLO\s*-+\s*\d+\s*CX', _replace_exemplo, doc)

        # Posologias de exemplo no template — o template tem a mesma posologia de exemplo repetida
        # Precisamos substituir cada ocorrência: ímpar=pos1, par=pos2
        _pos_counter = [0]
        posologia_template = 'Tomar 01 comprimido via oral de 12/12h por 03 dias'

        def _replace_posologia(match):
            _pos_counter[0] += 1
            if _pos_counter[0] % 2 == 1:
                return medicamento1_posologia if medicamento1_posologia else ''
            else:
                return medicamento2_posologia if medicamento2_posologia else ''

        doc = re.sub(re.escape(posologia_template), _replace_posologia, doc)

        # Limpar prefixo "2." que sobra quando med2 está vazio
        if not medicamento2_nome:
            # Remove linhas "2.  " seguidas de espaço/traço que restam no XML
            doc = re.sub(r'>2\.\s*<', '><', doc)

        _write_file(doc_path, doc)

    # Reempacotar
    pack_docx(unpack_dir, output_path)

    # Limpar
    shutil.rmtree(work_dir, ignore_errors=True)

    return output_path


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

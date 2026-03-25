"""
Gerador de APACs — Manipulação XML do template TEMPLATE_APAC_ISOLADO.docx
Cada chamada gera UMA APAC para um procedimento específico.
"""
import os
import shutil
import re
from app.utils.unpack import unpack_docx
from app.utils.pack import pack_docx

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '..', 'templates', 'TEMPLATE_APAC_ISOLADO.docx')


def gerar_apac(
    output_path: str,
    nome_paciente: str,
    data: str,
    diagnostico: str,
    cid: str,
    regiao: str,
    procedimento: str,
    justificativa: str,
    quantidade: str = "01",
    incidencia_rx: str = "",
    temp_dir: str = "/tmp",
    clinica: str = "FISIOMED"
):
    """
    Gera uma APAC individual.

    Args:
        output_path: Caminho do .docx de saída
        nome_paciente: Nome completo do paciente (maiúsculas)
        data: Data no formato DD/MM/AAAA
        diagnostico: Diagnóstico principal
        cid: CID do diagnóstico (ex: M75.1)
        regiao: Região afetada (ex: OMBRO DIREITO)
        procedimento: Procedimento solicitado (ex: FISIOTERAPIA MOTORA DE OMBRO DIREITO)
        justificativa: Texto da justificativa/observação
        quantidade: "01" para exames, "20" para fisioterapia
        incidencia_rx: Incidência de RX (ex: AP E PERFIL) — vazio para demais
        temp_dir: Diretório temporário para trabalho
    """
    # 1. Copiar template para temp
    work_dir = os.path.join(temp_dir, f'apac_{os.getpid()}_{id(output_path)}')
    unpack_dir = os.path.join(work_dir, 'unpacked')

    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    # Copiar template
    temp_docx = os.path.join(work_dir, 'template.docx')
    shutil.copy2(TEMPLATE_PATH, temp_docx)

    # 2. Desempacotar
    unpack_docx(temp_docx, unpack_dir)

    # 3. Editar core.xml
    core_path = os.path.join(unpack_dir, 'docProps', 'core.xml')
    if os.path.exists(core_path):
        core = _read_file(core_path)

        # dc:subject → NOME DO PACIENTE
        core = _replace_tag_content(core, 'dc:subject', nome_paciente)

        # cp:keywords → CID (ATENÇÃO: usar contexto completo da tag para evitar colisão)
        core = core.replace(
            '<cp:keywords>CID</cp:keywords>',
            f'<cp:keywords>{cid}</cp:keywords>'
        )

        # cp:category → REGIÃO
        core = _replace_tag_content(core, 'cp:category', regiao)

        # cp:contentStatus → INCIDÊNCIA (só para RX)
        core = _replace_tag_content(core, 'cp:contentStatus', incidencia_rx)

        # dc:creator → Nome da clínica (dinâmico)
        core = _replace_tag_content(core, 'dc:creator', clinica)

        # dc:description → QUANTIDADE
        core = _replace_tag_content(core, 'dc:description', quantidade)

        _write_file(core_path, core)

    # 4. Editar app.xml
    app_path = os.path.join(unpack_dir, 'docProps', 'app.xml')
    if os.path.exists(app_path):
        app = _read_file(app_path)
        # Company → DIAGNÓSTICO
        app = _replace_tag_content(app, 'Company', diagnostico)
        _write_file(app_path, app)

    # 5. Editar customXml/item1.xml
    item1_path = os.path.join(unpack_dir, 'customXml', 'item1.xml')
    if os.path.exists(item1_path):
        item1 = _read_file(item1_path)
        # CompanyFax → PROCEDIMENTO
        item1 = _replace_tag_content(item1, 'CompanyFax', procedimento)
        # CompanyPhone → JUSTIFICATIVA
        item1 = _replace_tag_content(item1, 'CompanyPhone', justificativa)
        _write_file(item1_path, item1)

    # 6. Editar document.xml
    doc_path = os.path.join(unpack_dir, 'word', 'document.xml')
    if os.path.exists(doc_path):
        doc = _read_file(doc_path)

        # Nome do paciente (placeholder inclui exemplo)
        doc = doc.replace(
            'NOME DO PACIENTE (EX: JOSÉ CARLOS)',
            nome_paciente
        )
        # Fallback: tentar sem o exemplo
        doc = doc.replace(
            'NOME DO PACIENTE',
            nome_paciente
        )

        # Nome da clínica (dinâmico)
        doc = doc.replace('NOME DA CLÍNICA', clinica)

        # Diagnóstico principal (placeholder no app.xml já tratado)
        doc = doc.replace(
            'DIAGNOSTICO PRINCIPAL (EX: HERNIA DISCAL LOMBAR)',
            diagnostico
        )

        # CID no document.xml: substituir >CID< por >cid_real<
        # Usar regex para pegar exatamente <w:t>CID</w:t> e variantes
        doc = re.sub(
            r'(>)CID(<)',
            rf'\g<1>{cid}\g<2>',
            doc,
            count=0  # substituir todas as ocorrências
        )

        # Quantidade: substituir >Núm.< por >quantidade<
        doc = doc.replace('>Núm.<', f'>{quantidade}<')

        # IMPORTANTE: Substituir justificativa PRIMEIRO (antes de "SOLICITAÇÃO")
        # porque "JUSTIFICATIVA DA SOLICITAÇÃO" contém a palavra "SOLICITAÇÃO"
        doc = doc.replace('JUSTIFICATIVA DA SOLICITAÇÃO', justificativa)

        # Solicitação/procedimento (agora que "JUSTIFICATIVA DA SOLICITAÇÃO" já foi tratada)
        doc = doc.replace('>SOLICITAÇÃO<', f'>{procedimento}<')
        doc = doc.replace('SOLICITAÇÃO', procedimento)

        # Data — buscar data do template (formato DD/MM/AAAA)
        doc = re.sub(r'\d{2}/\d{2}/\d{4}', data, doc)

        _write_file(doc_path, doc)

    # 7. Reempacotar
    pack_docx(unpack_dir, output_path)

    # Limpar temp
    shutil.rmtree(work_dir, ignore_errors=True)

    return output_path


def _replace_tag_content(xml_str, tag_name, new_value):
    """Substitui o conteúdo de uma tag XML pelo novo valor."""
    pattern = re.compile(
        rf'(<{tag_name}[^>]*>)(.*?)(</{tag_name}>)',
        re.DOTALL
    )

    def replacer(m):
        return m.group(1) + new_value + m.group(3)

    return pattern.sub(replacer, xml_str, count=1)


def _read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

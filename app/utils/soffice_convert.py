import subprocess
import os


def convert_to_pdf(docx_path, output_dir):
    """Converte .docx para .pdf usando LibreOffice headless."""
    subprocess.run([
        'libreoffice', '--headless', '--convert-to', 'pdf',
        '--outdir', output_dir, docx_path
    ], check=True, timeout=60)

    pdf_name = os.path.splitext(os.path.basename(docx_path))[0] + '.pdf'
    return os.path.join(output_dir, pdf_name)

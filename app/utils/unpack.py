import zipfile
import os
import shutil


def unpack_docx(docx_path, output_dir):
    """Desempacota .docx para diretório."""
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    with zipfile.ZipFile(docx_path, 'r') as z:
        z.extractall(output_dir)
    return output_dir

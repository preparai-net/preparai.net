import zipfile
import os


def pack_docx(source_dir, output_path):
    """Reempacota diretório como .docx."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as z:
        # [Content_Types].xml primeiro
        ct_path = os.path.join(source_dir, '[Content_Types].xml')
        if os.path.exists(ct_path):
            z.write(ct_path, '[Content_Types].xml')

        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_name = os.path.relpath(file_path, source_dir)
                if arc_name == '[Content_Types].xml':
                    continue  # já adicionado
                z.write(file_path, arc_name)
    return output_path

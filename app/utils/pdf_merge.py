from pypdf import PdfWriter


def merge_pdfs(pdf_paths, output_path):
    """Merge múltiplos PDFs em um único arquivo."""
    writer = PdfWriter()
    for pdf_path in pdf_paths:
        writer.append(pdf_path)
    writer.write(output_path)
    writer.close()
    return output_path

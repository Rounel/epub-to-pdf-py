"""
EPUB to PDF Converter
Usage:  python main.py input.epub [output.pdf]
GUI:    python gui.py
"""

import sys
import os
import base64
import mimetypes
import argparse
from pathlib import Path
from typing import Callable

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from xhtml2pdf import pisa

# Type alias for the optional log callback
LogCallback = Callable[[str], None]


def _log(msg: str, callback: LogCallback | None) -> None:
    if callback:
        callback(msg)
    else:
        print(msg)


def extract_epub_content(
    epub_path: str, log: LogCallback | None = None
) -> tuple[str, list[dict]]:
    """Extract title and ordered HTML chapters from an EPUB file."""
    book = epub.read_epub(epub_path)
    title = book.title or Path(epub_path).stem

    # Collect all image items for embedding
    images: dict[str, bytes] = {}
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        images[item.get_name()] = item.get_content()
        images[item.file_name] = item.get_content()

    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        raw_html = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(raw_html, "html.parser")

        # Inline images as base64 data URIs
        for img_tag in soup.find_all("img"):
            src = img_tag.get("src", "")
            img_name = src.lstrip("./")
            img_data = images.get(src) or images.get(img_name)
            if img_data:
                mime, _ = mimetypes.guess_type(src)
                mime = mime or "image/png"
                b64 = base64.b64encode(img_data).decode()
                img_tag["src"] = f"data:{mime};base64,{b64}"

        body = soup.find("body")
        content = str(body) if body else str(soup)
        chapters.append({"name": item.get_name(), "content": content})

    return title, chapters


def build_html_document(title: str, chapters: list[dict]) -> str:
    """Combine all chapters into a single styled HTML document."""
    css = """
        @page {
            size: A4;
            margin: 2.5cm 2cm 3cm 2cm;
            @frame footer {
                -pdf-frame-content: page-footer;
                bottom: 1cm;
                margin-left: 0;
                margin-right: 0;
                height: 1cm;
            }
        }
        body {
            font-family: Georgia, serif;
            font-size: 11pt;
            line-height: 1.7;
            color: #1a1a1a;
            text-align: justify;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: Arial, sans-serif;
            color: #111;
            margin-top: 1.2em;
            margin-bottom: 0.4em;
        }
        h1 { font-size: 22pt; }
        h2 { font-size: 15pt; border-bottom: 1px solid #ccc; padding-bottom: 3px; }
        h3 { font-size: 13pt; }
        p  { margin: 0.4em 0; }
        img { max-width: 100%; display: block; margin: 0.8em auto; }
        pre, code {
            font-family: Courier, monospace;
            font-size: 9pt;
            background: #f5f5f5;
            border: 1px solid #ddd;
            padding: 2px 4px;
        }
        pre { padding: 0.6em; white-space: pre-wrap; }
        blockquote {
            border-left: 3px solid #ccc;
            margin: 0.8em 0;
            padding: 0.4em 0.8em;
            color: #555;
        }
        table { width: 100%; border-collapse: collapse; margin: 0.8em 0; }
        th, td { border: 1px solid #ccc; padding: 5px 8px; }
        th { background: #f0f0f0; font-weight: bold; }
        a  { color: #2563eb; }
        .chapter-break { page-break-before: always; }
        .book-title {
            text-align: center;
            font-size: 26pt;
            font-family: Arial, sans-serif;
            margin-top: 6cm;
            margin-bottom: 2cm;
            color: #111;
        }
        #page-footer {
            text-align: center;
            font-size: 9pt;
            color: #888;
        }
    """

    body_parts = [f'<h1 class="book-title">{title}</h1>']
    for i, chapter in enumerate(chapters):
        css_class = "chapter-break" if i > 0 else ""
        body_parts.append(f'<div class="{css_class}">{chapter["content"]}</div>')

    # xhtml2pdf page-number tags
    footer = '<div id="page-footer">Page <pdf:pagenumber/> / <pdf:pagecount/></div>'

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>{css}</style>
</head>
<body>
  {footer}
  {''.join(body_parts)}
</body>
</html>"""


def convert_epub_to_pdf(
    epub_path: str,
    pdf_path: str,
    log: LogCallback | None = None,
) -> None:
    """Convert an EPUB file to PDF.

    Args:
        epub_path: Path to the source .epub file.
        pdf_path:  Path for the output .pdf file.
        log:       Optional callback receiving progress messages.
                   Defaults to print() when None.
    """
    _log(f"Lecture du fichier EPUB : {epub_path}", log)
    title, chapters = extract_epub_content(epub_path, log)
    _log(f"  Titre       : {title}", log)
    _log(f"  Chapitres   : {len(chapters)}", log)

    _log("Construction du document HTML...", log)
    html_content = build_html_document(title, chapters)

    _log("Rendu PDF en cours (cela peut prendre un moment)...", log)
    with open(pdf_path, "wb") as pdf_file:
        status = pisa.CreatePDF(html_content, dest=pdf_file)
    if status.err:
        raise RuntimeError(f"Erreur de rendu xhtml2pdf (code {status.err})")

    size_kb = Path(pdf_path).stat().st_size / 1024
    _log(f"PDF enregistré : {pdf_path}  ({size_kb:.1f} Ko)", log)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convertit un fichier EPUB en PDF.")
    parser.add_argument("epub", help="Chemin vers le fichier .epub source")
    parser.add_argument(
        "pdf",
        nargs="?",
        help="Chemin du fichier .pdf de sortie (défaut : même nom que l'EPUB)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.epub):
        print(f"Erreur : fichier introuvable : {args.epub}")
        sys.exit(1)

    pdf_path = args.pdf or str(Path(args.epub).with_suffix(".pdf"))
    convert_epub_to_pdf(args.epub, pdf_path)


if __name__ == "__main__":
    main()

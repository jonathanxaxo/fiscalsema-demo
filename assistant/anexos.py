"""Ler e descartar: TR ou contrato anexado no chat do Arise (Sprint 32).

O arquivo chega só na memória (``InMemoryOnlyUploadHandler``), o texto é
extraído aqui, vai para o prompt daquela pergunta e é descartado no fim da
requisição. Nada é gravado em disco, ``/tmp``, banco ou Vercel.

Proteções:
- tipo real conferido pela assinatura (``%PDF-`` ou ZIP com ``word/document.xml``),
  não pela extensão;
- até ``MAX_BYTES`` (4 MB), PDF até ``MAX_PDF_PAGES`` páginas, PDF com senha recusado;
- DOCX lido com a biblioteca padrão; recusa DOCTYPE/ENTIDADES (XXE e "bilhão de
  risadas") e limita o tamanho descompactado ("bomba de ZIP");
- texto limitado a ``MAX_TEXT_CHARS``; acima disso, avisa que leu só o início.
"""

import io
import time
import zipfile
from dataclasses import dataclass
from xml.etree import ElementTree

from django.core.files.uploadhandler import MemoryFileUploadHandler, StopUpload

MAX_BYTES = 4 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_BYTES + 64 * 1024  # arquivo + campos do formulário
MAX_PDF_PAGES = 100
MAX_TEXT_CHARS = 40_000
MAX_DOCX_XML_BYTES = 15 * 1024 * 1024
MAX_DOCX_TOTAL_BYTES = 40 * 1024 * 1024
MAX_DOCX_RATIO = 100
W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KINDS = {"pdf": "PDF", "docx": "DOCX"}


class AttachmentError(Exception):
    """Recusa com mensagem segura para a pessoa."""


@dataclass(frozen=True)
class Attachment:
    name: str
    kind: str
    size: int
    pages: int
    text: str
    truncated: bool
    ms: int

    def audit(self):
        """Somente metadados (nunca o nome do arquivo nem o conteúdo)."""
        return {"tipo": self.kind, "bytes": self.size, "paginas": self.pages,
                "truncado": self.truncated, "ms_leitura": self.ms}


class InMemoryOnlyUploadHandler(MemoryFileUploadHandler):
    """Mantém o upload só na memória, até o limite; nunca usa arquivo temporário."""

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        # O tamanho total já foi conferido na view (``MAX_REQUEST_BYTES``).
        self.activated = True

    def new_file(self, *args, **kwargs):
        self.received = 0
        super().new_file(*args, **kwargs)

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > MAX_BYTES:
            self.request.arise_upload_too_big = True
            raise StopUpload(connection_reset=False)
        return super().receive_data_chunk(raw_data, start)


def safe_name(name):
    name = str(name or "documento").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(ch for ch in name if ch.isprintable() and ch not in '<>"\'`')
    return (name or "documento")[:80]


def _clean(text):
    lines = (" ".join(line.split()) for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _limit(text):
    if len(text) > MAX_TEXT_CHARS:
        return text[:MAX_TEXT_CHARS], True
    return text, False


def _read_pdf(data):
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise AttachmentError("Este PDF tem senha. Envie uma versão sem senha.")
        pages = len(reader.pages)
        if pages > MAX_PDF_PAGES:
            raise AttachmentError(f"O PDF tem {pages} páginas; o limite é {MAX_PDF_PAGES}.")
        parts, total = [], 0
        for page in reader.pages:
            piece = page.extract_text() or ""
            parts.append(piece)
            total += len(piece)
            if total > MAX_TEXT_CHARS:
                break
    except AttachmentError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, AttributeError, RecursionError, OSError) as exc:
        raise AttachmentError("Não consegui abrir este PDF. Verifique se o arquivo não está corrompido.") from exc
    text = _clean("\n".join(parts))
    if len(text) < 20:
        raise AttachmentError(
            "Não consegui ler o texto deste PDF (parece ser uma imagem). Envie a versão em texto ou DOCX."
        )
    return text, pages


def _read_docx(data):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
        total = sum(info.file_size for info in infos)
        packed = max(1, sum(info.compress_size for info in infos))
        if total > MAX_DOCX_TOTAL_BYTES or total / packed > MAX_DOCX_RATIO:
            raise AttachmentError("Arquivo DOCX recusado: conteúdo compactado suspeito ou grande demais.")
        try:
            info = archive.getinfo("word/document.xml")
        except KeyError as exc:
            raise AttachmentError("Este arquivo não é um documento do Word (DOCX) válido.") from exc
        if info.file_size > MAX_DOCX_XML_BYTES:
            raise AttachmentError("O texto deste DOCX é grande demais.")
        xml = archive.read(info)
    except AttachmentError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError, RuntimeError) as exc:
        raise AttachmentError("Não consegui abrir este DOCX. Verifique se o arquivo não está corrompido.") from exc
    upper = xml.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise AttachmentError("Arquivo DOCX recusado por conter definições XML não permitidas.")
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise AttachmentError("Não consegui ler o texto deste DOCX.") from exc
    paragraphs = []
    for paragraph in root.iter(f"{W_NS}p"):
        pieces = []
        for node in paragraph.iter():
            if node.tag == f"{W_NS}t" and node.text:
                pieces.append(node.text)
            elif node.tag in (f"{W_NS}tab", f"{W_NS}br"):
                pieces.append(" ")
        paragraphs.append("".join(pieces))
    text = _clean("\n".join(paragraphs))
    if not text:
        raise AttachmentError("Este DOCX não tem texto para ler.")
    return text, 0


def read_attachment(uploaded):
    """Lê o arquivo enviado (em memória) e devolve um ``Attachment``. Não grava nada."""
    started = time.monotonic()
    name = safe_name(getattr(uploaded, "name", ""))
    size = getattr(uploaded, "size", 0) or 0
    if size <= 0:
        raise AttachmentError("O arquivo está vazio.")
    if size > MAX_BYTES:
        raise AttachmentError("O arquivo passa de 4 MB. Envie um arquivo menor.")
    data = uploaded.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise AttachmentError("O arquivo passa de 4 MB. Envie um arquivo menor.")
    if data.startswith(b"%PDF-"):
        kind, (text, pages) = "pdf", _read_pdf(data)
    elif data.startswith(b"PK\x03\x04"):
        kind, (text, pages) = "docx", _read_docx(data)
    else:
        raise AttachmentError("Envie somente PDF ou DOCX (o tipo real do arquivo não confere).")
    del data
    text, truncated = _limit(text)
    return Attachment(name=name, kind=KINDS[kind], size=size, pages=pages, text=text,
                      truncated=truncated, ms=int((time.monotonic() - started) * 1000))

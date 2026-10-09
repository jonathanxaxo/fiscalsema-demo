import hashlib
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


ALLOWED_TYPES = {
    ".pdf": ("application/pdf",),
    ".png": ("image/png",),
    ".jpg": ("image/jpeg",),
    ".jpeg": ("image/jpeg",),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"),
    ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"),
    ".odt": ("application/vnd.oasis.opendocument.text", "application/zip"),
}


def inspect_upload(upload):
    original_name = Path(upload.name or "").name
    if not original_name or original_name != upload.name or any(ord(c) < 32 for c in original_name):
        raise ValidationError("Nome de arquivo inválido.")
    if len(original_name) > 255:
        raise ValidationError("O nome do arquivo excede 255 caracteres.")
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_TYPES:
        raise ValidationError("Extensão não permitida. Use PDF, PNG, JPG, DOCX, XLSX ou ODT.")
    if upload.size <= 0 or upload.size > settings.DOCUMENT_MAX_UPLOAD_SIZE:
        raise ValidationError("O arquivo deve possuir conteúdo e ter no máximo 20 MB.")
    claimed = (getattr(upload, "content_type", "") or "").split(";", 1)[0].strip().lower()
    if claimed not in ALLOWED_TYPES[extension]:
        raise ValidationError("O tipo MIME informado não corresponde à extensão do arquivo.")

    head = upload.read(16)
    upload.seek(0)
    if extension == ".pdf" and not head.startswith(b"%PDF-"):
        raise ValidationError("O conteúdo não corresponde a um PDF válido.")
    if extension == ".png" and head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValidationError("O conteúdo não corresponde a uma imagem PNG válida.")
    if extension in {".jpg", ".jpeg"} and not head.startswith(b"\xff\xd8\xff"):
        raise ValidationError("O conteúdo não corresponde a uma imagem JPEG válida.")
    if extension in {".docx", ".xlsx", ".odt"}:
        _validate_office_archive(upload, extension)

    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return {
        "original_name": original_name,
        "mime_type": ALLOWED_TYPES[extension][0],
        "file_size": upload.size,
        "sha256": digest.hexdigest(),
    }


def _validate_office_archive(upload, extension):
    try:
        with zipfile.ZipFile(upload) as archive:
            entries = archive.infolist()
            names = {entry.filename for entry in entries}
            if len(entries) > 5000 or sum(entry.file_size for entry in entries) > 200 * 1024 * 1024:
                raise ValidationError("Arquivo compactado excede os limites de segurança.")
            if any(entry.flag_bits & 0x1 for entry in entries):
                raise ValidationError("Arquivos protegidos por senha não são aceitos.")
            valid = (
                extension == ".docx" and "[Content_Types].xml" in names and any(n.startswith("word/") for n in names)
            ) or (
                extension == ".xlsx" and "[Content_Types].xml" in names and any(n.startswith("xl/") for n in names)
            ) or (
                extension == ".odt" and "mimetype" in names
                and archive.read("mimetype") == b"application/vnd.oasis.opendocument.text"
            )
            if not valid:
                raise ValidationError("O conteúdo do arquivo Office/ODT não corresponde à extensão.")
    except (zipfile.BadZipFile, OSError):
        raise ValidationError("Arquivo Office/ODT inválido.")
    finally:
        upload.seek(0)

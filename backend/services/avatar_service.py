from pathlib import Path
from tempfile import SpooledTemporaryFile
from uuid import uuid4
import shutil

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB


def _validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Недопустимое расширение файла аватара")
    return extension


def _detect_file_type(header: bytes) -> str | None:
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return ".gif"
    if (
        header.startswith(b"RIFF")
        and len(header) >= 12
        and header[8:12] == b"WEBP"
    ):
        return ".webp"
    return None


def _validate_file_content(stream, expected_extension: str) -> None:
    if hasattr(stream, "seek"):
        stream.seek(0)

    # Проверяем формат файла по сигнатуре, а не по имени.
    header = stream.read(16)
    actual_extension = _detect_file_type(header)

    if actual_extension is None:
        raise ValueError("Недопустимый формат файла аватара")

    if expected_extension in {".jpg", ".jpeg"} and actual_extension == ".jpg":
        pass
    elif actual_extension != expected_extension:
        raise ValueError("Расширение файла не соответствует его содержимому")

    if hasattr(stream, "seek"):
        stream.seek(0)


def _validate_file_size(stream) -> None:
    if hasattr(stream, "seek") and hasattr(stream, "tell"):
        current_position = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(current_position)
        if size > MAX_AVATAR_SIZE:
            raise ValueError("Размер файла аватара превышает 5 МБ")
        return

    size = 0
    while chunk := stream.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_AVATAR_SIZE:
            raise ValueError("Размер файла аватара превышает 5 МБ")

    if hasattr(stream, "seek"):
        stream.seek(0)


def _prepare_stream(stream):
    if hasattr(stream, "seek") and hasattr(stream, "tell"):
        stream.seek(0)
        return stream

    buffered = SpooledTemporaryFile(max_size=MAX_AVATAR_SIZE)
    while chunk := stream.read(1024 * 1024):
        buffered.write(chunk)
        if buffered.tell() > MAX_AVATAR_SIZE:
            buffered.close()
            raise ValueError("Размер файла аватара превышает 5 МБ")

    buffered.seek(0)
    return buffered


def delete_avatar(path: str) -> None:
    """Удаляет файл аватара из storage/avatars, если он существует."""
    if not path:
        return

    project_root = Path(__file__).resolve().parents[2]
    avatars_dir = (project_root / "storage" / "avatars").resolve()

    relative_path = path.removeprefix("/")
    file_path = (project_root / relative_path).resolve()

    if avatars_dir not in file_path.parents:
        return

    file_path.unlink(missing_ok=True)


def save_avatar(file) -> str:
    """Сохраняет аватар в storage/avatars и возвращает URL-путь к файлу."""
    project_root = Path(__file__).resolve().parents[2]
    avatars_dir = project_root / "storage" / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    original_name = getattr(file, "filename", "") or ""
    extension = _validate_extension(original_name)
    source_stream = getattr(file, "file", file)
    stream = _prepare_stream(source_stream)

    try:
        _validate_file_content(stream, extension)
        _validate_file_size(stream)

        filename = f"{uuid4()}{extension}"
        destination = avatars_dir / filename

        if hasattr(stream, "seek"):
            stream.seek(0)

        with destination.open("wb") as output:
            shutil.copyfileobj(stream, output)
    finally:
        if stream is not source_stream:
            stream.close()

    return f"/storage/avatars/{filename}"

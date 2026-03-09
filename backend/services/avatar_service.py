from pathlib import Path
from uuid import uuid4
import shutil


def save_avatar(file) -> str:
    """Сохраняет аватар в storage/avatars и возвращает URL-путь к файлу."""
    project_root = Path(__file__).resolve().parents[2]
    avatars_dir = project_root / "storage" / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    original_name = getattr(file, "filename", "") or ""
    extension = Path(original_name).suffix
    filename = f"{uuid4()}{extension}"

    destination = avatars_dir / filename
    stream = getattr(file, "file", file)

    if hasattr(stream, "seek"):
        stream.seek(0)

    with destination.open("wb") as output:
        shutil.copyfileobj(stream, output)

    return f"/storage/avatars/{filename}"

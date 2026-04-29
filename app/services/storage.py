from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class LocalCoverStorage:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_cover(self, upload: UploadFile) -> str:
        suffix = Path(upload.filename or "cover.jpg").suffix or ".jpg"
        file_name = f"{uuid4().hex}{suffix.lower()}"
        destination = self.base_dir / file_name
        content = await upload.read()
        destination.write_bytes(content)
        return file_name

    def url_for(self, object_key: str) -> str:
        return f"/media/{object_key}"


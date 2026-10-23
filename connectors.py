"""Read-only local/NAS filesystem connector.

For a company deployment, mount the company share into the application host
and set COMPANY_DATA_ROOT. No credentials or file contents leave the host.
"""

import os
from pathlib import Path

import config


class LocalFilesystemConnector:
    def __init__(self, root: str):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError("Configured connector root is not an existing directory")

    def files(self):
        max_bytes = config.MAX_CONNECTOR_FILE_SIZE_MB * 1024 * 1024
        for path in self.root.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if path.suffix.lower().lstrip(".") not in config.ALLOWED_UPLOAD_EXTENSIONS:
                continue
            try:
                resolved = path.resolve()
                if self.root not in resolved.parents or path.stat().st_size > max_bytes:
                    continue
                yield resolved.relative_to(self.root).as_posix()
            except OSError:
                continue

    def file_count(self) -> int:
        return sum(1 for _ in self.files())


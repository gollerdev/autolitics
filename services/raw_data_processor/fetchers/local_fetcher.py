import os
from pathlib import Path
from typing import Iterator
 
from .base_fetcher import BaseFetcher
 
 
class LocalFetcher(BaseFetcher):
    """Reads run HTML files from the local filesystem.
    Uses LOCAL_DATA_ROOT env var as the prefix for message['base_path']."""
 
    def __init__(self, message: dict):
        super().__init__(message)
        self.local_root = Path(os.getenv("LOCAL_DATA_ROOT", "data"))
        self.run_folder = self.local_root / self.base_path
 
    def get_htmls(self) -> Iterator[str]:
        if not self.run_folder.exists():
            raise FileNotFoundError(f"Run folder not found: {self.run_folder}")
 
        html_files = sorted(self.run_folder.glob("offset_*.html"))
        print(f"Found {len(html_files)} HTML files in {self.run_folder}")
 
        for html_file in html_files:
            with open(html_file, "r", encoding="utf-8") as f:
                yield f.read()
import os
 
 
class LocalStorageService:
    """Stores files on the local filesystem.
    Drop-in replacement for S3StorageService when running locally.
    """
 
    def __init__(self, base_path: str = "data"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
 
    def save(self, key: str, content: str | bytes) -> str:
        """Save content to a file. Key is the relative path, e.g. 'raw/run_id/offset_0.html'.
        Returns the full path where the file was saved."""
        full_path = os.path.join(self.base_path, key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
 
        mode = "wb" if isinstance(content, bytes) else "w"
        encoding = None if isinstance(content, bytes) else "utf-8"
 
        with open(full_path, mode, encoding=encoding) as f:
            f.write(content)
 
        return full_path
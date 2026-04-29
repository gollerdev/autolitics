from .base_fetcher import BaseFetcher
from .local_fetcher import LocalFetcher
from .s3_fetcher import S3Fetcher
 
 
def get_fetcher(message: dict) -> BaseFetcher:
    """Build the right fetcher based on the message's storage_backend."""
    backend = message.get("storage_backend", "local")
    if backend == "s3":
        return S3Fetcher(message)
    return LocalFetcher(message)
 
 
__all__ = ["BaseFetcher", "LocalFetcher", "S3Fetcher", "get_fetcher"]
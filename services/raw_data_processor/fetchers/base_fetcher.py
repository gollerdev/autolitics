from abc import ABC, abstractmethod
from typing import Iterator
 
 
class BaseFetcher(ABC):
    """Abstract fetcher. Yields HTML content for every page in a run.
    Initialized with the run metadata message (from SQS)."""
 
    def __init__(self, message: dict):
        self.message = message
        self.run_id = message["run_id"]
        self.base_path = message["base_path"]
 
    @abstractmethod
    def get_htmls(self) -> Iterator[str]:
        """Yield the HTML content of every page in the run."""
        ...
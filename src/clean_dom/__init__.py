from importlib.metadata import PackageNotFoundError, version

from .pruner import CleaningResult, CleaningStats, DOMCleaner, ElementInfo

try:
    __version__ = version("clean-dom")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = [
    "CleaningResult",
    "CleaningStats",
    "DOMCleaner",
    "ElementInfo",
    "__version__",
]

from importlib.metadata import PackageNotFoundError, version

from .pruner import DOMCleaner

try:
	__version__ = version("clean-dom")
except PackageNotFoundError:
	__version__ = "0+unknown"

__all__ = ["DOMCleaner", "__version__"]

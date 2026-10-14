"""Compatibility entry point for the repository's fixture benchmark suite."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from benchmarks.run_benchmarks import main

if __name__ == "__main__":
    raise SystemExit(main())

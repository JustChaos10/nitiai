"""CLI entry point for the Retention Reasoning Agent."""

import sys
from pathlib import Path

# Add examples to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "examples"))

from simple_example import main

if __name__ == "__main__":
    main()

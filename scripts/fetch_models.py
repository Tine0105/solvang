"""Thin wrapper around scripts/build_catalog.py (--only-models)."""
import sys
from scripts.build_catalog import main

if __name__ == '__main__':
    if '--only-models' not in sys.argv and '--verify' not in sys.argv:
        sys.argv.append('--only-models')
    raise SystemExit(main())

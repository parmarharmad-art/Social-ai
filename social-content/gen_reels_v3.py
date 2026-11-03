#!/usr/bin/env python3
"""v3 entry point for book reels; uses the established renderer and requires neural voice."""
import os, runpy, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
RENDERER=HERE/"gen_reels.py"
if not RENDERER.is_file(): raise SystemExit("Missing base renderer: %s"%RENDERER)
os.environ.setdefault("REQUIRE_VOICE","1")
os.environ.setdefault("SKIP_EXISTING","0")
sys.argv=[str(RENDERER),*sys.argv[1:]]
runpy.run_path(str(RENDERER),run_name="__main__")

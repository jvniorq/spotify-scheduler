from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _ensure_src_importable() -> None:
    """Allow execution of this file directly during PyInstaller builds."""
    package_root = Path(__file__).resolve().parents[1]
    if str(package_root) not in sys.path:
        sys.path.insert(0, str(package_root))


def main() -> None:
    _ensure_src_importable()

    parser = argparse.ArgumentParser(description="Spoxu · Automatización musical")
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="Inicia oculto/minimizado.",
    )
    args = parser.parse_args()

    from spotify_scheduler_pro.app import run

    run(start_minimized=args.minimized)


if __name__ == "__main__":
    main()

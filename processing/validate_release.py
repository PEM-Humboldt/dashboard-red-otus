"""Valida integridad, contratos y cobertura de una publicación procesada.

Desarrollo: Cristian C. Acevedo, Ingeniero de Soluciones.
Supervisión: Angélica Diaz Pulido, Instituto Humboldt.
Versión: v2026.1.0. Licencia: MIT.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from red_otus_pipeline.validation import validate_release


def main() -> None:
    """Valida la publicación indicada y presenta su resumen."""
    parser = argparse.ArgumentParser(description="Valida la publicación activa Silver/Gold")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_release(args.output.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

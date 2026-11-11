"""Inicia el procesamiento Red OTUS 2026 desde la línea de comandos.

Desarrollo: Cristian C. Acevedo, Ingeniero de Soluciones.
Supervisión: Angélica Diaz Pulido, Instituto Humboldt.
Versión: v2026.1.0. Licencia: MIT.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from red_otus_pipeline.cli import main

if __name__ == "__main__":
    main()

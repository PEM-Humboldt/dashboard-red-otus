"""Inicia la interfaz gráfica del procesamiento Red OTUS 2026.

Desarrollo: Cristian C. Acevedo, Ingeniero de Soluciones.
Supervisión: Angélica Diaz Pulido, Instituto Humboldt.
Versión: v2026.1.0. Licencia: MIT.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from red_otus_pipeline.gui import main

if __name__ == "__main__":
    main()

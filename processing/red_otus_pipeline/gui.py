"""Interfaz PySide6 para configurar, ejecutar y revisar el procesamiento."""

from __future__ import annotations

import json
import os
import threading
import traceback
import webbrowser
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QCompleter, QDateEdit, QDialog, QDialogButtonBox,
    QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QTabBar, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from . import __version__
from .config import PipelineConfig
from .engine import run_pipeline
from .gallery import GalleryCancelled, GalleryConfig, optimize_gallery
from .input_inspection import InputInspection, inspect_input


APP_NAME = "Generador de datos para el Dashboard Red OTUS"
TIMEZONE = "America/Bogota"
INTERVALS = (
    ("Sin filtro temporal", 0, "Conserva todos los registros válidos."),
    ("30 minutos", 30, "Aplica una separación mínima de 30 minutos."),
    ("1 hora", 60, "Aplica una separación mínima de una hora."),
    ("24 horas", 1440, "Aplica una separación mínima de 24 horas."),
)


def _format_duration(seconds: float) -> str:
    total_seconds = max(0, round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _format_integer(value: int | float) -> str:
    return f"{int(value):,}".replace(",", ".")


def _format_percent(value: float) -> str:
    return f"{value:.1f}".replace(".", ",") + " %"


def _format_decimal(value: float, digits: int = 1) -> str:
    text = f"{value:,.{digits}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def _format_file_size(value: int | float) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            digits = 0 if unit == "B" else 1
            return f"{size:.{digits}f} {unit}".replace(".", ",")
        size /= 1024
    return f"{size:.1f} GB".replace(".", ",")


class ScrollSafeDateEdit(QDateEdit):
    """Evita que la rueda del ratón cambie una fecha accidentalmente."""

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class ScrollSafeTabBar(QTabBar):
    """Evita que la rueda del ratón cambie la pestaña activa."""

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        event.ignore()


class ScrollSafeTabWidget(QTabWidget):
    """Contenedor de pestañas protegido contra cambios por desplazamiento."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTabBar(ScrollSafeTabBar(self))


class ProcessingCancelled(Exception):
    """Indica que el usuario solicitó detener el procesamiento."""


def _project_root() -> Path:
    current = Path(__file__).resolve()
    working_directory = Path.cwd().resolve()
    candidates = (*current.parents, working_directory, *working_directory.parents)
    for candidate in candidates:
        if (candidate / "processing").is_dir() and (candidate / "dashboard").is_dir():
            return candidate
        if (candidate / ".git").exists() and (candidate / "processing").is_dir():
            return candidate
    return current.parents[2]


def _resources_dir() -> Path:
    return Path(__file__).resolve().parent / "resources"


class ProjectSelectionDialog(QDialog):
    """Permite buscar y seleccionar los proyectos que se publicarán."""

    def __init__(self, projects, selected: set[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Seleccionar proyectos")
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        intro = QLabel("Seleccione los proyectos que desea procesar. Puede buscar por identificador, nombre o corporación.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        controls = QHBoxLayout()
        self.search = QLineEdit(placeholderText="Buscar proyecto…")
        select_all = QPushButton("Seleccionar todos")
        clear_all = QPushButton("Limpiar selección")
        controls.addWidget(self.search, 1)
        controls.addWidget(select_all)
        controls.addWidget(clear_all)
        layout.addLayout(controls)
        self.table = QTableWidget(len(projects), 5)
        self.table.setHorizontalHeaderLabels(["Procesar", "ID", "Proyecto", "Eventos", "Corporación estimada"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        for table_row, (_, row) in enumerate(projects.iterrows()):
            project_id = str(row["project_id"])
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Checked if project_id in selected else Qt.CheckState.Unchecked)
            check.setData(Qt.ItemDataRole.UserRole, project_id)
            self.table.setItem(table_row, 0, check)
            self.table.setItem(table_row, 1, QTableWidgetItem(project_id))
            self.table.setItem(table_row, 2, QTableWidgetItem(str(row["project_name"])))
            self.table.setItem(table_row, 3, QTableWidgetItem(str(row["events"])))
            self.table.setItem(table_row, 4, QTableWidgetItem(str(row["corporation"])))
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.search.textChanged.connect(self._filter)
        select_all.clicked.connect(lambda: self._set_visible(True))
        clear_all.clicked.connect(lambda: self._set_visible(False))

    def _filter(self, value: str) -> None:
        term = value.strip().casefold()
        for row in range(self.table.rowCount()):
            text = " ".join(self.table.item(row, column).text() for column in (1, 2, 4)).casefold()
            self.table.setRowHidden(row, bool(term and term not in text))

    def _set_visible(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            if not self.table.isRowHidden(row):
                self.table.item(row, 0).setCheckState(state)

    def selected_ids(self) -> set[str]:
        """Devuelve los identificadores marcados por el usuario."""
        return {
            str(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
            for row in range(self.table.rowCount())
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked
        }


class GallerySummaryDialog(QDialog):
    """Presenta el resultado de la galería en un diseño compacto."""

    def __init__(self, summary: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        published = bool(summary.get("published"))
        self.setWindowTitle("Galería preparada" if published else "Galería no publicada")
        self.setModal(True)
        self.setMinimumWidth(470)
        self.setMaximumWidth(560)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(14)
        heading = QLabel(
            "Las copias optimizadas ya están disponibles en el dashboard."
            if published
            else "La galería anterior se conservó porque se encontraron archivos con error.",
            objectName="sectionTitle",
        )
        heading.setWordWrap(True)
        layout.addWidget(heading)
        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(7)
        values = (
            ("Imágenes encontradas", _format_integer(summary.get("found", 0))),
            ("Optimizadas", _format_integer(summary.get("processed", 0))),
            ("Sin cambios", _format_integer(summary.get("skipped", 0))),
            ("Con error", _format_integer(summary.get("failed", 0))),
            ("Peso de los originales", _format_file_size(summary.get("original_bytes", 0))),
            ("Peso de las copias", _format_file_size(summary.get("optimized_bytes", 0))),
            ("Reducción", _format_percent(summary.get("saved_percent", 0))),
        )
        for row, (label, value) in enumerate(values):
            grid.addWidget(QLabel(label, objectName="fieldLabel"), row, 0)
            grid.addWidget(QLabel(value), row, 1)
        layout.addLayout(grid)
        detail = QLabel(
            "Consulte processing_reports/gallery_optimization.csv para revisar el detalle por archivo.",
            objectName="hint",
        )
        detail.setWordWrap(True)
        layout.addWidget(detail)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class PipelineWorker(QObject):
    """Ejecuta el pipeline sin bloquear la interfaz."""

    progress = Signal(str, float, str)
    completed = Signal(dict)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, config: PipelineConfig) -> None:
        super().__init__()
        self.config = config
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Solicita la cancelación cooperativa de la ejecución."""
        self._cancel_event.set()

    def _progress(self, stage: str, value: float, message: str) -> None:
        if self._cancel_event.is_set():
            raise ProcessingCancelled()
        self.progress.emit(stage, value, message)

    @Slot()
    def run(self) -> None:
        """Ejecuta el pipeline y comunica su resultado mediante señales."""
        try:
            result = run_pipeline(self.config, self._progress)
            self.completed.emit(result)
        except ProcessingCancelled:
            self.cancelled.emit()
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            self.finished.emit()


class GalleryWorker(QObject):
    """Ejecuta la optimización sin bloquear la interfaz."""

    progress = Signal(int, int, str)
    completed = Signal(dict)
    failed = Signal(str)
    cancelled = Signal()
    finished = Signal()

    def __init__(self, config: GalleryConfig) -> None:
        super().__init__()
        self.config = config
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Solicita la cancelación cooperativa de la galería."""
        self._cancel_event.set()

    def _progress(self, current: int, total: int, message: str) -> None:
        if self._cancel_event.is_set():
            raise GalleryCancelled()
        self.progress.emit(current, total, message)

    @Slot()
    def run(self) -> None:
        """Optimiza la galería y comunica su resultado mediante señales."""
        try:
            result = optimize_gallery(self.config, self._progress)
            self.completed.emit(result)
        except GalleryCancelled:
            self.cancelled.emit()
        except Exception:
            self.failed.emit(traceback.format_exc())
        finally:
            self.finished.emit()


class PipelineWindow(QMainWindow):
    """Ventana principal para validación, parametrización y publicación."""
    def __init__(self) -> None:
        super().__init__()
        self.root_path = _project_root()
        self.inspection: InputInspection | None = None
        self.selected_projects: set[str] = set()
        self.corporation_overrides: dict[str, str] = {}
        self.worker_thread: QThread | None = None
        self.worker: PipelineWorker | None = None
        self.gallery_worker_thread: QThread | None = None
        self.gallery_worker: GalleryWorker | None = None
        self.last_result: dict | None = None
        self._logged_stages: set[str] = set()
        self._execution_requires_reset = False
        self.setWindowTitle(f"{APP_NAME} · Versión {__version__}")
        self.setMinimumSize(1020, 760)
        self.resize(1180, 900)
        icon_path = _resources_dir() / "red_otus.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._build_ui()
        self._load_styles()
        self._connect_invalidation()
        self._update_process_enabled()

    def _load_styles(self) -> None:
        style_path = _resources_dir() / "styles.qss"
        if style_path.exists():
            stylesheet = style_path.read_text(encoding="utf-8")
            arrow_path = (_resources_dir() / "combo_arrow.svg").as_posix()
            stylesheet = stylesheet.replace(
                "url(combo_arrow.svg)", f'url("{arrow_path}")'
            )
            self.setStyleSheet(stylesheet)

    def _build_ui(self) -> None:
        central = QWidget(objectName="centralWidget")
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        header = QFrame(objectName="header")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(34, 22, 34, 22)
        title = QLabel(APP_NAME, objectName="appTitle", alignment=Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel(
            "Valida los archivos descargados de Wildlife Insights, prepara el modelo de datos y publica los resultados que utiliza el dashboard.",
            objectName="appSubtitle", alignment=Qt.AlignmentFlag.AlignCenter,
        )
        subtitle.setWordWrap(True)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root_layout.addWidget(header)
        scroll = QScrollArea(widgetResizable=True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 22, 24, 18)
        content_layout.setSpacing(16)
        self.paths_card = self._build_paths_card()
        self.parameters_card = self._build_parameters_card()
        self.gallery_card = self._build_gallery_card()
        content_layout.addWidget(self.paths_card)
        content_layout.addWidget(self.parameters_card)
        content_layout.addWidget(self.gallery_card)
        content_layout.addWidget(self._build_execution_card())
        scroll.setWidget(content)
        root_layout.addWidget(scroll, 1)
        footer = QLabel(
            f"Versión {__version__} · Desarrollo: Cristian C. Acevedo · "
            "Supervisión: Angélica Diaz Pulido · Instituto Humboldt, 2026.",
            objectName="footer", alignment=Qt.AlignmentFlag.AlignCenter,
        )
        footer.setWordWrap(True)
        footer.setContentsMargins(12, 10, 12, 12)
        root_layout.addWidget(footer)
        self.setCentralWidget(central)

    def _card(self, title: str, description: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(12)
        heading = QLabel(title, objectName="sectionTitle")
        detail = QLabel(description, objectName="sectionDescription")
        detail.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(detail)
        return card, layout

    def _build_paths_card(self) -> QWidget:
        card, layout = self._card(
            "1. Ubicación y validación de los insumos",
            "Seleccione la descarga de Wildlife Insights, el límite espacial de las corporaciones y la carpeta donde se publicarán los datos del dashboard.",
        )
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        self.raw_path = QLineEdit(str(self.root_path / "processing" / "input" / "raw"))
        self.output_path = QLineEdit(str(self.root_path / "dashboard" / "data"))
        self.reports_path = QLineEdit(str(self.root_path / "processing_reports"))
        self.shape_path = QLineEdit(str(self.root_path / "processing" / "input" / "spatial" / "CAR_MPIO.shp"))
        self._path_row(grid, 0, "Ruta de la carpeta con los archivos CSV descargados de Wildlife Insights", self.raw_path, True)
        self._path_row(grid, 1, "Carpeta de publicación para los datos procesados del dashboard", self.output_path, True)
        self._path_row(grid, 2, "Carpeta para informes de calidad y resúmenes del procesamiento", self.reports_path, True)
        self._path_row(grid, 3, "Archivo geográfico con los límites de las corporaciones ambientales", self.shape_path, False)
        layout.addLayout(grid)
        row = QHBoxLayout()
        self.validate_button = QPushButton("Validar carpetas y cargar proyectos", objectName="successButton")
        self.validation_status = QLabel("Pendiente de validación", objectName="hint")
        row.addWidget(self.validate_button)
        row.addWidget(self.validation_status, 1)
        layout.addLayout(row)
        self.validate_button.clicked.connect(self.validate_input)
        return card

    def _path_row(self, grid: QGridLayout, row: int, label: str, field: QLineEdit, directory: bool) -> None:
        caption = QLabel(label, objectName="fieldLabel")
        caption.setWordWrap(True)
        caption.setMaximumWidth(300)
        button = QPushButton("Examinar…")
        button.clicked.connect(lambda: self._browse(field, directory))
        grid.addWidget(caption, row, 0)
        grid.addWidget(field, row, 1)
        grid.addWidget(button, row, 2)

    def _build_parameters_card(self) -> QWidget:
        card, layout = self._card(
            "2. Parámetros del procesamiento",
            "Defina el periodo de análisis, los productos requeridos y los proyectos que harán parte de esta publicación.",
        )
        form = QGridLayout()
        form.setColumnStretch(1, 1)
        form.setColumnStretch(3, 1)
        self.initiative = QLineEdit("Red OTUS")
        self.dashboard_title = QLineEdit("Red OTUS")
        initiative_label = QLabel("Nombre de la iniciativa registrado en los datos", objectName="fieldLabel")
        initiative_label.setWordWrap(True)
        dashboard_title_label = QLabel("Texto visible en el encabezado del dashboard", objectName="fieldLabel")
        dashboard_title_label.setWordWrap(True)
        dashboard_title_label.setMaximumWidth(260)
        initiative_help = QLabel(
            "Se guarda como metadato de procedencia en la publicación y en la dimensión de proyectos. "
            "No modifica los filtros ni los cálculos.",
            objectName="hint",
        )
        initiative_help.setWordWrap(True)
        dashboard_title_help = QLabel(
            "Aparece después de «Reporte de Datos de Fototrampeo -» en la vista. "
            "Solo cambia el texto del encabezado.",
            objectName="hint",
        )
        dashboard_title_help.setWordWrap(True)
        form.addWidget(initiative_label, 0, 0)
        form.addWidget(self.initiative, 0, 1)
        form.addWidget(dashboard_title_label, 0, 2)
        form.addWidget(self.dashboard_title, 0, 3)
        form.addWidget(initiative_help, 1, 1)
        form.addWidget(dashboard_title_help, 1, 3)
        self.start_date = self._date_edit(QDate(2020, 1, 1))
        self.end_date = self._date_edit(QDate.currentDate())
        form.addWidget(QLabel("Fecha inicial del periodo", objectName="fieldLabel"), 2, 0)
        form.addWidget(self._date_field(self.start_date), 2, 1)
        form.addWidget(QLabel("Fecha final del periodo", objectName="fieldLabel"), 2, 2)
        form.addWidget(self._date_field(self.end_date), 2, 3)
        form.addWidget(QLabel(f"Zona horaria aplicada automáticamente: {TIMEZONE}", objectName="hint"), 3, 0, 1, 4)
        layout.addLayout(form)
        intervals_box = QGroupBox("Productos por intervalo entre registros")
        intervals_layout = QGridLayout(intervals_box)
        self.interval_checks: dict[int, QCheckBox] = {}
        for index, (label, minutes, tip) in enumerate(INTERVALS):
            check = QCheckBox(label, checked=True)
            check.setToolTip(tip)
            check.stateChanged.connect(self._update_process_enabled)
            self.interval_checks[minutes] = check
            intervals_layout.addWidget(check, index // 2, index % 2)
        self.interval_note = QLabel("Debe seleccionar al menos una opción.", objectName="hint")
        intervals_layout.addWidget(self.interval_note, 2, 0, 1, 2)
        layout.addWidget(intervals_box)
        project_row = QHBoxLayout()
        self.project_button = QPushButton("Seleccionar proyectos…", enabled=False)
        self.project_count = QLabel("Valide primero los archivos de entrada", objectName="hint")
        project_row.addWidget(QLabel("Proyectos incluidos en el procesamiento", objectName="fieldLabel"))
        project_row.addWidget(self.project_button)
        project_row.addWidget(self.project_count, 1)
        layout.addLayout(project_row)
        self.project_button.clicked.connect(self.choose_projects)
        override_box = QGroupBox("Reasignación manual de corporación")
        override_layout = QGridLayout(override_box)
        explanation = QLabel(
            "Utilice esta opción solo cuando la asignación espacial requiera una corrección conocida. La decisión quedará registrada en el reporte de calidad.",
            objectName="hint",
        )
        explanation.setWordWrap(True)
        self.override_project = QComboBox()
        self.override_corporation = QComboBox()
        self._enable_searchable_combo(self.override_project, "Escriba un ID o nombre de proyecto…")
        self._enable_searchable_combo(self.override_corporation, "Escriba el nombre o la sigla de la corporación…")
        self.override_apply = QPushButton("Aplicar reasignación")
        self.override_remove = QPushButton("Quitar reasignación")
        for widget in (self.override_project, self.override_corporation, self.override_apply, self.override_remove):
            widget.setEnabled(False)
        override_layout.addWidget(explanation, 0, 0, 1, 4)
        override_layout.addWidget(QLabel("Proyecto", objectName="fieldLabel"), 1, 0)
        override_layout.addWidget(self.override_project, 1, 1)
        override_layout.addWidget(QLabel("Corporación", objectName="fieldLabel"), 1, 2)
        override_layout.addWidget(self.override_corporation, 1, 3)
        self.override_status = QLabel("Sin reasignaciones manuales", objectName="hint")
        override_layout.addWidget(self.override_status, 2, 0, 1, 2)
        override_layout.addWidget(self.override_apply, 2, 2)
        override_layout.addWidget(self.override_remove, 2, 3)
        layout.addWidget(override_box)
        self.override_apply.clicked.connect(self.apply_override)
        self.override_remove.clicked.connect(self.remove_override)
        return card

    @staticmethod
    def _enable_searchable_combo(combo: QComboBox, placeholder: str) -> None:
        """Permite localizar opciones extensas escribiendo cualquier fragmento."""
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.setMaxVisibleItems(18)
        if combo.lineEdit() is not None:
            combo.lineEdit().setPlaceholderText(placeholder)
            combo.lineEdit().setClearButtonEnabled(True)
        completer = QCompleter(combo.model(), combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)

    def _date_edit(self, value: QDate) -> QDateEdit:
        widget = ScrollSafeDateEdit(value, calendarPopup=True, displayFormat="yyyy-MM-dd")
        widget.setMinimumDate(QDate(1900, 1, 1))
        widget.setMaximumDate(QDate(2100, 12, 31))
        return widget

    def _date_field(self, date_edit: QDateEdit) -> QWidget:
        container = QWidget()
        row = QVBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        row.addWidget(date_edit)
        row.addWidget(QLabel("Formato: AAAA-MM-DD. También puede usar el calendario.", objectName="hint"))
        return container

    def _build_gallery_card(self) -> QWidget:
        card, layout = self._card(
            "3. Preparación de imágenes para la galería",
            "Conserve aquí las fotografías originales de máxima resolución. La herramienta genera copias livianas para el dashboard sin modificar los archivos fuente.",
        )
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        self.gallery_source = QLineEdit(
            str(self.root_path / "processing" / "input" / "favorites_originals")
        )
        self.gallery_output = QLineEdit(
            str(self.root_path / "dashboard" / "www" / "images" / "favorites")
        )
        self.gallery_output.setReadOnly(True)
        self.gallery_browse = QPushButton("Examinar…")
        self.gallery_browse.clicked.connect(lambda: self._browse(self.gallery_source, True))
        source_label = QLabel("Carpeta de fotografías originales organizadas por proyecto", objectName="fieldLabel")
        source_label.setWordWrap(True)
        source_label.setMaximumWidth(300)
        output_label = QLabel("Carpeta de copias optimizadas que utiliza el dashboard", objectName="fieldLabel")
        output_label.setWordWrap(True)
        output_label.setMaximumWidth(300)
        grid.addWidget(source_label, 0, 0)
        grid.addWidget(self.gallery_source, 0, 1)
        grid.addWidget(self.gallery_browse, 0, 2)
        grid.addWidget(output_label, 1, 0)
        grid.addWidget(self.gallery_output, 1, 1, 1, 2)
        layout.addLayout(grid)
        guidance = QLabel(
            "Dentro de la carpeta de originales cree General para las vistas consolidadas y una carpeta con el project_id para cada proyecto. "
            "Se admiten JPG, JPEG y PNG. Las copias se limitan a 1.600 px y los JPEG se guardan con calidad 82 %.",
            objectName="hint",
        )
        guidance.setWordWrap(True)
        layout.addWidget(guidance)
        controls = QHBoxLayout()
        self.gallery_button = QPushButton("Optimizar y publicar imágenes", objectName="successButton")
        self.gallery_stop_button = QPushButton("Detener optimización", objectName="dangerButton", enabled=False)
        self.gallery_open_button = QPushButton("Abrir carpeta de originales")
        controls.addWidget(self.gallery_button)
        controls.addWidget(self.gallery_stop_button)
        controls.addWidget(self.gallery_open_button)
        controls.addStretch(1)
        layout.addLayout(controls)
        self.gallery_progress = QProgressBar(value=0)
        self.gallery_status = QLabel("Agregue o actualice los originales antes de ejecutar esta operación.", objectName="hint")
        layout.addWidget(self.gallery_progress)
        layout.addWidget(self.gallery_status)
        self.gallery_source.textChanged.connect(self._update_gallery_enabled)
        self.gallery_button.clicked.connect(self.start_gallery_optimization)
        self.gallery_stop_button.clicked.connect(self.stop_gallery_optimization)
        self.gallery_open_button.clicked.connect(self.open_gallery_source)
        self._update_gallery_enabled()
        return card

    def _build_execution_card(self) -> QWidget:
        card, layout = self._card(
            "4. Ejecución y control de calidad",
            "La publicación anterior solo se reemplaza después de completar y validar correctamente la nueva ejecución.",
        )
        buttons = QHBoxLayout()
        self.process_button = QPushButton("Procesar y publicar datos", objectName="primaryButton")
        self.stop_button = QPushButton("Detener procesamiento", objectName="dangerButton", enabled=False)
        self.clear_button = QPushButton("Limpiar para nueva ejecución", enabled=False)
        self.open_output_button = QPushButton("Abrir carpeta de datos publicados", enabled=False)
        buttons.addWidget(self.process_button)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.clear_button)
        buttons.addWidget(self.open_output_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.progress = QProgressBar(value=0)
        self.status = QLabel("Valide los archivos de entrada para comenzar.", objectName="hint")
        layout.addWidget(self.progress)
        layout.addWidget(self.status)
        self.tabs = ScrollSafeTabWidget()
        self.console = QPlainTextEdit(objectName="console", readOnly=True, minimumHeight=210)
        self.tabs.addTab(self.console, "Estado del procesamiento")
        self.project_summary_table = QTableWidget(0, 7)
        self.project_summary_table.setHorizontalHeaderLabels(
            ["ID", "Proyecto", "Corporación", "Cámaras", "Eventos", "Especies", "Observaciones"]
        )
        self.project_summary_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.project_summary_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tabs.addTab(self.project_summary_table, "Resumen por proyecto")
        quality_page = QWidget()
        quality_layout = QVBoxLayout(quality_page)
        quality_layout.setContentsMargins(10, 10, 10, 10)
        quality_help = QLabel(
            "Excluido por inconsistencia: el dato no se publicó porque falta información obligatoria o contiene valores incompatibles.  ·  "
            "Procesado con limitación: el dato se conservó, pero no puede utilizarse en una parte de la visualización.  ·  "
            "Resuelto automáticamente: el procesamiento aplicó una solución conservadora.  ·  "
            "Excluido por criterios de análisis: el dato quedó fuera por el periodo seleccionado o por una regla analítica."
        )
        quality_help.setWordWrap(True)
        quality_help.setObjectName("hint")
        quality_layout.addWidget(quality_help)
        self.quality_table = QTableWidget(0, 5)
        self.quality_table.setHorizontalHeaderLabels(
            ["Estado", "Situación identificada", "Resultado del procesamiento", "Registros afectados", "Recomendación"]
        )
        self.quality_table.verticalHeader().setVisible(False)
        self.quality_table.setWordWrap(True)
        self.quality_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.quality_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        for column, width in enumerate((190, 430, 530, 175, 530)):
            self.quality_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.quality_table.setColumnWidth(column, width)
        quality_layout.addWidget(self.quality_table)
        self.tabs.addTab(quality_page, "Resumen de calidad de los datos")
        detail_page = QWidget()
        detail_layout = QVBoxLayout(detail_page)
        detail_layout.setContentsMargins(24, 28, 24, 28)
        detail_layout.addStretch(1)
        detail_intro = QLabel(
            "El reporte completo presenta el resumen, ejemplos, recomendaciones y el detalle de los registros "
            "en un formato diseñado para su revisión en el navegador.", objectName="sectionDescription",
        )
        detail_intro.setWordWrap(True)
        detail_intro.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.open_report_button = QPushButton("Abrir reporte completo en el navegador", enabled=False)
        detail_button_row = QHBoxLayout()
        detail_button_row.addStretch(1)
        detail_button_row.addWidget(self.open_report_button)
        detail_button_row.addStretch(1)
        detail_layout.addWidget(detail_intro)
        detail_layout.addLayout(detail_button_row)
        detail_layout.addStretch(1)
        self.tabs.addTab(detail_page, "Detalle de calidad de los datos")
        for index in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(index, False)
        layout.addWidget(self.tabs)
        self.process_button.clicked.connect(self.start_processing)
        self.stop_button.clicked.connect(self.stop_processing)
        self.clear_button.clicked.connect(self.clear_execution)
        self.open_output_button.clicked.connect(self.open_output)
        self.open_report_button.clicked.connect(self.open_quality_report)
        return card

    def _connect_invalidation(self) -> None:
        self.raw_path.textChanged.connect(self.invalidate_input)
        self.shape_path.textChanged.connect(self.invalidate_input)
        for field in (self.output_path, self.reports_path, self.initiative, self.dashboard_title):
            field.textChanged.connect(self._update_process_enabled)
        self.start_date.dateChanged.connect(self._update_process_enabled)
        self.end_date.dateChanged.connect(self._update_process_enabled)

    def _browse(self, field: QLineEdit, directory: bool) -> None:
        current = field.text().strip()
        if directory:
            value = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta", current)
        else:
            value, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo espacial", str(Path(current).parent), "Shapefile (*.shp)")
        if value:
            field.setText(value)

    @Slot()
    def invalidate_input(self) -> None:
        """Invalida la revisión previa cuando cambian los insumos."""
        if self.inspection is None:
            return
        self.inspection = None
        self.selected_projects.clear()
        self.corporation_overrides.clear()
        self.project_button.setEnabled(False)
        self.project_count.setText("Las rutas cambiaron; vuelva a validar los archivos")
        self.validation_status.setText("Validación pendiente por cambios en las rutas")
        self._set_override_enabled(False)
        self._update_process_enabled()

    @Slot()
    def validate_input(self) -> None:
        """Revisa las rutas y carga el catálogo disponible."""
        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            raw = Path(self.raw_path.text()).expanduser().resolve()
            shape_text = self.shape_path.text().strip()
            shape = Path(shape_text).expanduser().resolve() if shape_text else None
            self.inspection = inspect_input(raw, shape)
            self.selected_projects = set(self.inspection.projects["project_id"].astype(str))
            self.corporation_overrides.clear()
            self.project_button.setEnabled(True)
            self._populate_override_controls()
            self._update_project_count()
            self.validation_status.setText(
                f"Validación completada: {len(self.inspection.projects)} proyectos y {self.inspection.image_files} archivos de imágenes."
            )
            self._log("[VALIDACIÓN] Archivos requeridos disponibles.")
            self._log(f"[VALIDACIÓN] Proyectos encontrados: {len(self.inspection.projects):,}")
            self._log(f"[VALIDACIÓN] Archivos images_*.csv: {self.inspection.image_files:,}")
            for warning in self.inspection.warnings:
                self._log(f"[ADVERTENCIA] {warning}")
            self._update_process_enabled()
        except Exception as exc:
            self.inspection = None
            self.validation_status.setText("La validación no fue satisfactoria")
            QMessageBox.critical(self, "Validación de insumos", str(exc))
            self._update_process_enabled()
        finally:
            QApplication.restoreOverrideCursor()

    def _populate_override_controls(self) -> None:
        self.override_project.clear()
        self.override_corporation.clear()
        if self.inspection is None:
            self._set_override_enabled(False)
            return
        for _, row in self.inspection.projects.iterrows():
            self.override_project.addItem(f"{row['project_id']} · {row['project_name']}", str(row["project_id"]))
        self.override_corporation.addItems(list(self.inspection.corporations))
        self._set_override_enabled(bool(self.inspection.corporations))

    def _set_override_enabled(self, enabled: bool) -> None:
        for widget in (self.override_project, self.override_corporation, self.override_apply, self.override_remove):
            widget.setEnabled(enabled)

    @Slot()
    def choose_projects(self) -> None:
        """Abre la selección de proyectos incluidos en la ejecución."""
        if self.inspection is None:
            return
        dialog = ProjectSelectionDialog(self.inspection.projects, self.selected_projects, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected = dialog.selected_ids()
            if not selected:
                QMessageBox.warning(self, "Selección de proyectos", "Debe seleccionar al menos un proyecto.")
                return
            self.selected_projects = selected
            self.corporation_overrides = {project: corporation for project, corporation in self.corporation_overrides.items() if project in selected}
            self._update_project_count()
            self._update_override_status()
            self._update_process_enabled()

    def _update_project_count(self) -> None:
        if self.inspection is None:
            return
        total = len(self.inspection.projects)
        selected = len(self.selected_projects)
        suffix = "Todos los proyectos" if selected == total else "Selección personalizada"
        self.project_count.setText(f"{selected} de {total} proyectos seleccionados · {suffix}")

    @Slot()
    def apply_override(self) -> None:
        """Registra una reasignación manual de corporación."""
        project_id = self.override_project.currentData()
        corporation = self.override_corporation.currentText().strip()
        if project_id and corporation:
            self.corporation_overrides[str(project_id)] = corporation
            self._update_override_status()

    @Slot()
    def remove_override(self) -> None:
        """Retira la reasignación del proyecto seleccionado."""
        project_id = self.override_project.currentData()
        if project_id:
            self.corporation_overrides.pop(str(project_id), None)
            self._update_override_status()

    def _update_override_status(self) -> None:
        count = len(self.corporation_overrides)
        self.override_status.setText("Sin reasignaciones manuales" if count == 0 else f"{count} proyecto(s) con reasignación manual")

    def _selected_intervals(self) -> tuple[int, ...]:
        return tuple(minutes for minutes, check in self.interval_checks.items() if check.isChecked())

    def _configuration(self) -> PipelineConfig:
        if self.inspection is None:
            raise ValueError("Valide los archivos de entrada antes de iniciar el procesamiento")
        start, end = self.start_date.date(), self.end_date.date()
        all_projects = set(self.inspection.projects["project_id"].astype(str))
        selected = () if self.selected_projects == all_projects else tuple(sorted(self.selected_projects))
        shape_text = self.shape_path.text().strip()
        config = PipelineConfig(
            raw_path=Path(self.raw_path.text()).expanduser().resolve(),
            output_path=Path(self.output_path.text()).expanduser().resolve(),
            reports_path=Path(self.reports_path.text()).expanduser().resolve(),
            shapefile_path=Path(shape_text).expanduser().resolve() if shape_text else None,
            initiative_name=self.initiative.text().strip(), dashboard_title=self.dashboard_title.text().strip(),
            timezone=TIMEZONE, start_date=date(start.year(), start.month(), start.day()),
            cutoff_date=date(end.year(), end.month(), end.day()), independence_minutes=self._selected_intervals(),
            selected_projects=selected, corporation_overrides=tuple(sorted(self.corporation_overrides.items())),
        )
        config.validate()
        return config

    @Slot()
    def _update_process_enabled(self) -> None:
        valid_dates = self.start_date.date() <= self.end_date.date() if hasattr(self, "start_date") else False
        running = bool(
            (self.worker_thread and self.worker_thread.isRunning())
            or (self.gallery_worker_thread and self.gallery_worker_thread.isRunning())
        )
        enabled = bool(
            self.inspection is not None and self.selected_projects and self._selected_intervals()
            and self.initiative.text().strip() and self.dashboard_title.text().strip()
            and self.output_path.text().strip() and self.reports_path.text().strip()
            and valid_dates and not running
            and not self._execution_requires_reset
        )
        if hasattr(self, "process_button"):
            self.process_button.setEnabled(enabled)
        if hasattr(self, "interval_note"):
            labels = [label for label, minutes, _ in INTERVALS if minutes in self._selected_intervals()]
            self.interval_note.setText("Se generarán: " + ", ".join(labels) if labels else "Debe seleccionar al menos una opción.")

    @Slot()
    def _update_gallery_enabled(self) -> None:
        running = bool(
            (self.worker_thread and self.worker_thread.isRunning())
            or (self.gallery_worker_thread and self.gallery_worker_thread.isRunning())
        )
        source_ready = bool(getattr(self, "gallery_source", None) and self.gallery_source.text().strip())
        if hasattr(self, "gallery_button"):
            self.gallery_button.setEnabled(source_ready and not running)

    @Slot()
    def start_gallery_optimization(self) -> None:
        """Inicia la preparación independiente de la galería."""
        source = Path(self.gallery_source.text()).expanduser().resolve()
        config = GalleryConfig(
            source_root=source,
            output_root=Path(self.gallery_output.text()).expanduser().resolve(),
            reports_root=Path(self.reports_path.text()).expanduser().resolve(),
        )
        try:
            config.validate()
        except Exception as exc:
            QMessageBox.warning(self, "Preparación de la galería", str(exc))
            return
        self.gallery_progress.setValue(0)
        self.gallery_status.setText("Revisando y optimizando las fotografías…")
        self.gallery_button.setEnabled(False)
        self.gallery_stop_button.setEnabled(True)
        self.gallery_browse.setEnabled(False)
        self.gallery_source.setEnabled(False)
        self.gallery_worker_thread = QThread(self)
        self.gallery_worker = GalleryWorker(config)
        self.gallery_worker.moveToThread(self.gallery_worker_thread)
        self.gallery_worker_thread.started.connect(self.gallery_worker.run)
        self.gallery_worker.progress.connect(self._on_gallery_progress)
        self.gallery_worker.completed.connect(self._on_gallery_completed)
        self.gallery_worker.cancelled.connect(self._on_gallery_cancelled)
        self.gallery_worker.failed.connect(self._on_gallery_failed)
        self.gallery_worker.finished.connect(self.gallery_worker_thread.quit)
        self.gallery_worker.finished.connect(self.gallery_worker.deleteLater)
        self.gallery_worker_thread.finished.connect(self.gallery_worker_thread.deleteLater)
        self.gallery_worker_thread.finished.connect(self._on_gallery_finished)
        self.gallery_worker_thread.start()
        self._update_process_enabled()

    @Slot(int, int, str)
    def _on_gallery_progress(self, current: int, total: int, message: str) -> None:
        self.gallery_progress.setValue(round(current / total * 100) if total else 0)
        self.gallery_status.setText(f"{current} de {total}: {message}")

    @Slot(dict)
    def _on_gallery_completed(self, result: dict) -> None:
        summary = result["summary"]
        if summary.get("published"):
            self.gallery_progress.setValue(100)
            self.gallery_status.setText(
                f"Publicación finalizada: {summary['processed']} optimizadas y "
                f"{summary['skipped']} reutilizadas. Reducción: {_format_percent(summary['saved_percent'])}."
            )
        else:
            self.gallery_status.setText(
                f"No se publicó la nueva galería: {summary['failed']} archivo(s) requieren revisión. "
                "La versión anterior permanece disponible."
            )
        GallerySummaryDialog(summary, self).exec()

    @Slot()
    def stop_gallery_optimization(self) -> None:
        """Solicita detener la preparación de la galería."""
        if (
            self.gallery_worker is None
            or self.gallery_worker_thread is None
            or not self.gallery_worker_thread.isRunning()
        ):
            return
        self.gallery_worker.cancel()
        self.gallery_stop_button.setEnabled(False)
        self.gallery_status.setText(
            "Deteniendo de forma segura… La galería publicada continuará sin cambios."
        )

    @Slot()
    def _on_gallery_cancelled(self) -> None:
        self.gallery_status.setText(
            "Optimización detenida. La galería publicada se conservó sin cambios."
        )

    @Slot(str)
    def _on_gallery_failed(self, detail: str) -> None:
        last_line = next((line.strip() for line in reversed(detail.splitlines()) if line.strip()), "Error no identificado")
        self.gallery_status.setText(f"No fue posible preparar la galería: {last_line}")
        QMessageBox.critical(
            self,
            "Preparación de la galería",
            "La operación no pudo completarse. Los archivos publicados previamente se conservaron. "
            f"Detalle: {last_line}",
        )

    @Slot()
    def _on_gallery_finished(self) -> None:
        self.gallery_worker_thread = None
        self.gallery_worker = None
        self.gallery_stop_button.setEnabled(False)
        self.gallery_browse.setEnabled(True)
        self.gallery_source.setEnabled(True)
        self._update_gallery_enabled()
        self._update_process_enabled()

    @Slot()
    def open_gallery_source(self) -> None:
        """Abre la carpeta configurada para imágenes originales."""
        path = Path(self.gallery_source.text()).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)  # type: ignore[attr-defined]

    @Slot()
    def start_processing(self) -> None:
        """Inicia el procesamiento con la configuración validada."""
        try:
            config = self._configuration()
        except Exception as exc:
            QMessageBox.critical(self, "Configuración", str(exc))
            return
        self.last_result = None
        self._execution_requires_reset = True
        self._logged_stages.clear()
        self.console.clear()
        self.quality_table.setRowCount(0)
        self.project_summary_table.setRowCount(0)
        self.tabs.setCurrentIndex(0)
        self._set_result_tabs_enabled(False)
        self.progress.setValue(0)
        self.open_output_button.setEnabled(False)
        self.open_report_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.paths_card.setEnabled(False)
        self.parameters_card.setEnabled(False)
        self.gallery_card.setEnabled(False)
        self.status.setText("Iniciando procesamiento…")
        self._log("RED OTUS · PROCESAMIENTO 2026")
        self._log(f"Periodo solicitado: {config.start_date.isoformat()} a {config.cutoff_date.isoformat()}")
        self._log(f"Proyectos: {len(self.selected_projects):,}")
        self._log("Intervalos: " + ", ".join("sin filtro" if value == 0 else f"{value} min" for value in config.independence_minutes))
        if config.corporation_overrides:
            self._log(f"Reasignaciones manuales de corporación: {len(config.corporation_overrides)}")
        self.worker_thread = QThread(self)
        self.worker = PipelineWorker(config)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.completed.connect(self._on_completed)
        self.worker.cancelled.connect(self._on_cancelled)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._on_worker_finished)
        self.worker_thread.start()
        self._update_process_enabled()

    @Slot()
    def stop_processing(self) -> None:
        """Solicita detener el procesamiento activo."""
        if self.worker is None or self.worker_thread is None or not self.worker_thread.isRunning():
            return
        self.worker.cancel()
        self.stop_button.setEnabled(False)
        self.status.setText("Deteniendo el procesamiento de forma segura…")
        self._log("Cancelación solicitada. Se conservará la publicación anterior.")

    @Slot()
    def clear_execution(self) -> None:
        """Restablece el estado visible de la ejecución."""
        if self.worker_thread and self.worker_thread.isRunning():
            return
        self._execution_requires_reset = False
        self.last_result = None
        self._logged_stages.clear()
        self.console.clear()
        self.quality_table.setRowCount(0)
        self.project_summary_table.setRowCount(0)
        self.tabs.setCurrentIndex(0)
        self._set_result_tabs_enabled(False)
        self.progress.setValue(0)
        self.status.setText("Revise los parámetros y ejecute un nuevo procesamiento.")
        self.open_output_button.setEnabled(False)
        self.open_report_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.clear_button.setEnabled(False)
        self.paths_card.setEnabled(True)
        self.parameters_card.setEnabled(True)
        self.gallery_card.setEnabled(True)
        self.project_button.setEnabled(self.inspection is not None)
        self._populate_override_controls()
        self._update_process_enabled()

    @Slot(str, float, str)
    def _on_progress(self, stage: str, value: float, message: str) -> None:
        self.progress.setValue(round(value * 100))
        self.status.setText(message)
        stage_messages = {
            "bronze": "Lectura y consolidación de los archivos de entrada.",
            "silver": "Validación, limpieza y normalización de los datos.",
            "gold": "Cálculo de los productos requeridos por el dashboard.",
            "publish": "Validación y publicación segura de los resultados.",
            "done": "Ejecución completada correctamente.",
        }
        if stage not in self._logged_stages:
            self._logged_stages.add(stage)
            self._log(stage_messages.get(stage, message))

    @Slot(dict)
    def _on_completed(self, result: dict) -> None:
        self.last_result = result
        self.progress.setValue(100)
        self.status.setText("Procesamiento finalizado y datos publicados correctamente.")
        self.open_output_button.setEnabled(True)
        self.open_report_button.setEnabled(Path(result["quality_report_path"]).is_file())
        self._render_result(result)
        self._set_result_tabs_enabled(True)

    @Slot()
    def _on_cancelled(self) -> None:
        self.status.setText("Procesamiento detenido. La publicación anterior se conservó sin cambios.")
        self._log("Procesamiento detenido de forma segura. Use 'Limpiar para nueva ejecución' para continuar.")

    @Slot(str)
    def _on_failed(self, detail: str) -> None:
        last_line = next((line.strip() for line in reversed(detail.splitlines()) if line.strip()), "Error no identificado")
        self._log(f"La ejecución no pudo completarse: {last_line}")
        self.status.setText("El procesamiento no finalizó. La publicación anterior se conservó sin cambios.")
        if "WinError 5" in detail or "PermissionError" in detail or "Acceso denegado" in detail:
            message = (
                "Windows mantuvo temporalmente ocupada la carpeta de resultados y no permitió activar la nueva "
                "publicación. La versión anterior se conservó sin cambios. Cierre cualquier ventana del Explorador, "
                "dashboard o reporte que esté usando esa carpeta y vuelva a intentarlo."
            )
        else:
            message = (
                "No fue posible completar la ejecución. La publicación anterior se conservó sin cambios. "
                "Revise el último mensaje en 'Estado del procesamiento' antes de intentarlo nuevamente."
            )
        QMessageBox.critical(self, "Procesamiento no completado", message)

    @Slot()
    def _on_worker_finished(self) -> None:
        self.worker_thread = None
        self.worker = None
        self.stop_button.setEnabled(False)
        self.clear_button.setEnabled(True)
        self.paths_card.setEnabled(False)
        self.parameters_card.setEnabled(False)
        self.gallery_card.setEnabled(True)
        self._update_gallery_enabled()
        self._update_process_enabled()

    def _set_result_tabs_enabled(self, enabled: bool) -> None:
        for index in range(1, self.tabs.count()):
            self.tabs.setTabEnabled(index, enabled)

    def _render_result(self, result: dict) -> None:
        raw, silver = result.get("raw_counts", {}), result.get("silver_counts", {})
        observations_read = int(raw.get("images", 0))
        observations_published = int(silver.get("fact_observation", 0))
        observations_not_published = max(0, observations_read - observations_published)
        published_percent = 100 * observations_published / observations_read if observations_read else 0.0
        excluded_percent = 100 - published_percent if observations_read else 0.0
        self._log("")
        self._log("RESUMEN FINAL")
        self._log(f"Identificador de ejecución: {result['run_id']}")
        self._log(f"Tiempo total: {_format_duration(float(result['elapsed_seconds']))} (hh:mm:ss)")
        self._log(f"Uso promedio equivalente de CPU: {_format_percent(float(result['cpu_average_percent']))}")
        self._log(f"Memoria máxima observada: {_format_decimal(float(result['memory_peak_sampled_mb']), 2)} MB")
        self._log("")
        self._log("BALANCE DE OBSERVACIONES")
        self._log(f"Observaciones leídas desde los archivos images: {_format_integer(observations_read)}")
        self._log(
            f"Observaciones incluidas en los datos publicados: {_format_integer(observations_published)} "
            f"({_format_percent(published_percent)})"
        )
        self._log(
            f"Observaciones no incluidas por periodo, integridad o criterios analíticos: "
            f"{_format_integer(observations_not_published)} ({_format_percent(excluded_percent)})"
        )
        report: dict = {}
        report_path = Path(result["quality_report_json_path"])
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            user_rules = report.get("rules", [])
            self.quality_table.setRowCount(len(user_rules))
            for row, item in enumerate(user_rules):
                values = (
                    item.get("status", "Situación no clasificada"),
                    item.get("description", item.get("title", item.get("rule", ""))),
                    item.get("result", ""),
                    _format_integer(item.get("count", 0)),
                    item.get("recommendation", ""),
                )
                for column, value in enumerate(values):
                    self.quality_table.setItem(row, column, QTableWidgetItem(str(value)))
            self.quality_table.resizeRowsToContents()
        summary = result.get("project_summary", [])
        self.project_summary_table.setRowCount(len(summary))
        for row, item in enumerate(summary):
            values = (item.get("project_id", ""), item.get("proyecto", ""), item.get("corporacion", ""), item.get("camaras", 0), item.get("eventos", 0), item.get("especies", 0), item.get("observaciones", 0))
            for column, value in enumerate(values):
                self.project_summary_table.setItem(row, column, QTableWidgetItem(str(value)))
        self.project_summary_table.resizeRowsToContents()
        self._log("")
        self._log("RESULTADO")
        self._log("El procesamiento finalizó correctamente y la nueva publicación quedó disponible.")
        self._log(f"Datos publicados para el dashboard: {result['output_path']}")
        self._log(f"Informes del procesamiento: {result['reports_path']}")
        self._log(
            f"Archivos principales: {len(result.get('silver_counts', {}))} Parquet de datos validados, "
            f"{len(result.get('gold_counts', {}))} Parquet para el dashboard y manifiesto. "
            "Los reportes de calidad se conservaron fuera del paquete desplegable."
        )
        self._log("Revise las pestañas 'Resumen por proyecto', 'Resumen de calidad de los datos' y 'Detalle de calidad de los datos'.")

    def _log(self, message: str) -> None:
        self.console.appendPlainText(message)

    @Slot()
    def open_output(self) -> None:
        """Abre la carpeta de datos publicados."""
        path = Path(self.output_path.text()).expanduser().resolve()
        if path.exists():
            os.startfile(path)  # type: ignore[attr-defined]

    @Slot()
    def open_quality_report(self) -> None:
        """Abre el reporte HTML de la última ejecución."""
        if self.last_result:
            report = Path(self.last_result["quality_report_path"])
            if report.is_file():
                webbrowser.open(report.as_uri())

    def closeEvent(self, event: QCloseEvent) -> None:
        """Evita cerrar la ventana mientras exista una tarea activa."""
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.information(
                self,
                "Procesamiento en curso",
                "Espere a que finalice el procesamiento o utilice 'Detener procesamiento' antes de cerrar la aplicación.",
            )
            event.ignore()
            return
        if self.gallery_worker_thread and self.gallery_worker_thread.isRunning():
            QMessageBox.information(
                self,
                "Preparación de imágenes en curso",
                "Espere a que termine la optimización de la galería antes de cerrar la aplicación.",
            )
            event.ignore()
            return
        event.accept()


def main() -> None:
    """Configura Qt y abre la interfaz gráfica de procesamiento."""
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Instituto Humboldt")
    app.setApplicationVersion(__version__)
    window = PipelineWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

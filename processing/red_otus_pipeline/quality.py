"""Registra y clasifica las situaciones de calidad detectadas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


QUALITY_RULES: dict[str, dict[str, str]] = {
    "PROJECT_KEY_DUPLICATE": {
        "title": "El identificador de un proyecto aparece repetido",
        "description": "El mismo project_id aparece en más de una fila de projects.csv, por lo que no existe una única ficha para ese proyecto.",
        "recommendation": "Revise las filas indicadas en projects.csv y confirme en Wildlife Insights cuál contiene la información vigente del proyecto.",
        "status": "Resuelto automáticamente",
        "result": "El procesamiento conservó la primera fila disponible para cada project_id y descartó las repeticiones de esta ejecución.",
    },
    "DEPLOYMENT_KEY_DUPLICATE": {
        "title": "Una instalación de cámara aparece repetida",
        "description": "La misma combinación de proyecto, cámara, evento y fechas de instalación aparece más de una vez en deployments.csv.",
        "recommendation": "Revise las filas indicadas y deje una sola instalación cuando proyecto, deployment_id, evento, fecha inicial y fecha final sean iguales.",
        "status": "Resuelto automáticamente",
        "result": "El procesamiento conservó una sola instalación con esa combinación de campos y descartó las filas repetidas.",
    },
    "TIMESTAMP_INVALID": {
        "title": "La fecha y hora de captura está vacía o no es válida",
        "description": "El campo timestamp de la observación está vacío o contiene un valor que no puede interpretarse como una fecha y hora de captura.",
        "recommendation": "Revise el campo timestamp de la imagen indicada en Wildlife Insights. Complete la fecha y la hora o corrija su formato antes de descargar nuevamente los datos.",
        "status": "Excluido por inconsistencia",
        "result": "La observación se excluyó de la publicación porque sin una fecha y hora válidas no puede asignarse a un evento ni utilizarse en los cálculos temporales.",
    },
    "TIMESTAMP_BEFORE_START": {
        "title": "La observación es anterior al periodo seleccionado",
        "description": "La fecha de captura es anterior a la fecha inicial definida por el usuario para esta ejecución.",
        "recommendation": "No requiere corrección si la exclusión es esperada. Si debe incluirse, ejecute nuevamente el proceso con una fecha inicial anterior.",
        "status": "Excluido por criterios de análisis",
        "result": "La observación se excluyó únicamente por estar fuera del rango temporal solicitado; esto no implica un error en el dato.",
    },
    "TIMESTAMP_AFTER_END": {
        "title": "La observación es posterior al periodo seleccionado",
        "description": "La fecha de captura es posterior a la fecha final definida por el usuario para esta ejecución.",
        "recommendation": "No requiere corrección si la exclusión es esperada. Si debe incluirse, ejecute nuevamente el proceso con una fecha final posterior.",
        "status": "Excluido por criterios de análisis",
        "result": "La observación se excluyó únicamente por estar fuera del rango temporal solicitado; esto no implica un error en el dato.",
    },
    "DEPLOYMENT_EVENT_AMBIGUOUS": {
        "title": "Una observación coincide con más de una instalación de la misma cámara",
        "description": "El proyecto y el deployment_id llevan la observación a varias filas de deployments, generalmente porque sus periodos de instalación se superponen.",
        "recommendation": "Revise en deployments.csv las fechas start_date y end_date de esa cámara y ajuste en Wildlife Insights los periodos que se superponen si no corresponden a instalaciones distintas.",
        "status": "Resuelto automáticamente",
        "result": "El procesamiento priorizó la instalación cuyo intervalo contiene la fecha de captura; si persistió más de una opción, eligió de forma determinística el primer evento ordenado.",
    },
    "DEPLOYMENT_ORPHAN": {
        "title": "El proyecto y la cámara no aparecen en el archivo de instalaciones",
        "description": "La combinación de project_id y deployment_id de la observación no tiene una fila correspondiente en deployments.csv.",
        "recommendation": "Busque juntos project_id y deployment_id en el archivo images indicado y en deployments.csv. Corrija el identificador o complete la instalación faltante en Wildlife Insights antes de descargar nuevamente los datos.",
        "status": "Excluido por inconsistencia",
        "result": "La observación se excluyó de la publicación porque no fue posible asociarla con una instalación, un evento, un periodo de operación y una ubicación.",
    },
    "EVENT_NAME_MISSING": {
        "title": "La instalación no tiene un evento de muestreo asignado",
        "description": "La cámara sí aparece en deployments.csv, pero el campo subproject_name de esa instalación está vacío. Este campo identifica el evento de muestreo al que pertenecen sus observaciones.",
        "recommendation": "Revise la instalación indicada en Wildlife Insights, asigne el evento correspondiente en subproject_name con el formato AAAA_número, por ejemplo 2026_1, y descargue nuevamente los datos.",
        "status": "Excluido por inconsistencia",
        "result": "La observación se excluyó de la publicación porque, aunque la cámara existe, no puede asignarse a un evento de muestreo.",
    },
    "EVENT_CODE_INVALID": {
        "title": "El evento de muestreo no usa el formato requerido",
        "description": "El campo subproject_name de la instalación contiene un valor, pero no utiliza el formato AAAA_número, por ejemplo 2026_1.",
        "recommendation": "Revise subproject_name en la instalación indicada, corrija el nombre del evento en Wildlife Insights con el formato AAAA_número y descargue nuevamente los datos.",
        "status": "Excluido por inconsistencia",
        "result": "La observación se excluyó de la publicación porque no es posible identificar de forma confiable el año y el número de su evento de muestreo.",
    },
    "EVENT_YEAR_MISMATCH": {
        "title": "La fecha de captura no corresponde temporalmente al evento",
        "description": "El año del campo timestamp está fuera del margen permitido de un año antes o después del año registrado en subproject_name.",
        "recommendation": "Compare timestamp con subproject_name en la instalación indicada. Corrija la fecha de captura o asigne la cámara al evento correcto en Wildlife Insights antes de descargar nuevamente los datos.",
        "status": "Excluido por inconsistencia",
        "result": "La observación se excluyó de la publicación porque la diferencia entre el año de captura y el año del evento supera el margen temporal admitido.",
    },
    "TAXON_EXCLUDED": {
        "title": "La observación no permite construir un nombre científico válido",
        "description": "Los campos genus o species están vacíos o contienen valores como Unknown o No CV Result, por lo que no puede construirse sp_binomial.",
        "recommendation": "Revise en Wildlife Insights los campos genus y species de la identificación. Confirme también wi_taxon_id cuando exista y complete la clasificación antes de descargar nuevamente los datos.",
        "status": "Excluido por criterios de análisis",
        "result": "La observación se registra en el reporte de calidad, pero no se incorpora al dataset publicado ni a los indicadores, rankings o gráficas de biodiversidad.",
    },
    "COORDINATE_INVALID": {
        "title": "La instalación no puede ubicarse espacialmente",
        "description": "Los campos latitude o longitude están vacíos, no son numéricos o se encuentran fuera de los rangos geográficos válidos.",
        "recommendation": "Revise latitude y longitude en la instalación de Wildlife Insights: latitud entre -90 y 90 y longitud entre -180 y 180. Corrija los valores antes de descargar nuevamente los datos.",
        "status": "Procesado con limitación",
        "result": "La instalación se conserva, pero queda sin asignación espacial de corporación y no puede representarse correctamente en el mapa.",
    },
    "DEPLOYMENT_PERIOD_REVERSED": {
        "title": "La instalación tiene un periodo de operación inválido",
        "description": "El campo end_date es anterior a start_date, por lo que las fechas describen un periodo de instalación imposible.",
        "recommendation": "Revise start_date y end_date de la instalación en Wildlife Insights, corrija el orden de las fechas y descargue nuevamente los datos.",
        "status": "Excluido por inconsistencia",
        "result": "La instalación se excluyó de la publicación porque no es posible calcular un periodo de operación válido.",
    },
    "DEPLOYMENT_OUTSIDE_RANGE": {
        "title": "La instalación se encuentra completamente fuera del periodo seleccionado",
        "description": "El periodo comprendido entre start_date y end_date no se cruza con las fechas inicial y final elegidas para la ejecución.",
        "recommendation": "No requiere corrección si la exclusión es esperada. Si la instalación debe incluirse, amplíe el rango de fechas o revise start_date y end_date.",
        "status": "Excluido por criterios de análisis",
        "result": "La instalación se excluyó únicamente por no coincidir con el periodo solicitado; esto no implica un error en sus fechas.",
    },
    "MANUAL_CORPORATION_OVERRIDE": {
        "title": "La corporación del proyecto fue reasignada manualmente",
        "description": "La corporación calculada a partir de la ubicación fue reemplazada por la selección realizada por el usuario en la interfaz.",
        "recommendation": "Confirme que la corporación seleccionada corresponde al proyecto antes de desplegar los datos en el dashboard.",
        "status": "Configuración aplicada",
        "result": "La publicación utiliza la corporación elegida manualmente y conserva la decisión en el reporte de calidad.",
    },
}


@dataclass
class QualityIssue:
    """Situación de calidad vinculada con su registro de origen."""

    stage: str
    severity: str
    rule: str
    entity_type: str
    entity_id: str
    field: str
    original_value: str
    action: str
    source_file: str = ""
    source_row: int | None = None


class QualityLog:
    """Acumula incidencias y genera resúmenes orientados al usuario."""
    def __init__(self) -> None:
        self._issues: list[QualityIssue] = []

    @classmethod
    def from_frame(cls, frame: pd.DataFrame) -> "QualityLog":
        """Reconstruye el registro desde su tabla de detalle técnico."""
        log = cls()
        columns = list(QualityIssue.__dataclass_fields__)
        for record in frame.reindex(columns=columns).to_dict(orient="records"):
            source_row = record.get("source_row")
            record["source_row"] = int(source_row) if pd.notna(source_row) else None
            log.add(**record)
        return log

    def add(self, **kwargs: Any) -> None:
        """Agrega una situación de calidad."""
        self._issues.append(QualityIssue(**kwargs))

    def add_rows(
        self,
        frame: pd.DataFrame,
        *,
        stage: str,
        severity: str,
        rule: str,
        id_column: str,
        field: str,
        action: str,
    ) -> None:
        """Registra las filas afectadas por una misma regla."""
        if frame.empty:
            return
        for _, row in frame.iterrows():
            self.add(
                stage=stage,
                severity=severity,
                rule=rule,
                entity_type="row",
                entity_id=str(row.get(id_column, "")),
                field=field,
                original_value=str(row.get(field, "")),
                action=action,
                source_file=str(row.get("source_file", "")),
                source_row=int(row["source_row"]) if pd.notna(row.get("source_row")) else None,
            )

    def to_frame(self) -> pd.DataFrame:
        """Devuelve el detalle técnico como tabla."""
        columns = list(QualityIssue.__dataclass_fields__)
        return pd.DataFrame([asdict(x) for x in self._issues], columns=columns)

    def counts(self) -> dict[str, int]:
        """Resume los hallazgos por severidad técnica."""
        frame = self.to_frame()
        if frame.empty:
            return {"total": 0, "error": 0, "warning": 0, "info": 0}
        values = frame["severity"].value_counts().to_dict()
        return {"total": len(frame), **{x: int(values.get(x, 0)) for x in ("error", "warning", "info")}}

    def rule_counts(self) -> list[dict[str, Any]]:
        """Resume casos, ejemplos y acciones por regla."""
        frame = self.to_frame()
        if frame.empty:
            return []
        grouped = (
            frame.groupby(["stage", "severity", "rule", "action"], dropna=False)
            .size()
            .rename("count")
            .reset_index()
            .sort_values(["severity", "stage", "rule"])
        )
        rows = grouped.to_dict(orient="records")
        for row in rows:
            metadata = QUALITY_RULES.get(str(row["rule"]), {})
            row["title"] = metadata.get("title", str(row["rule"]))
            row["description"] = metadata.get("description", "Revise el detalle técnico de la incidencia.")
            row["recommendation"] = metadata.get("recommendation", "Valide el registro en los archivos de entrada.")
            row["status"] = metadata.get("status", "Situación no clasificada")
            row["result"] = metadata.get("result", "La regla fue aplicada durante el procesamiento.")
            subset = frame[
                frame["rule"].eq(row["rule"]) & frame["action"].eq(row["action"])
            ].copy()
            distinct_columns = ["source_file", "original_value"]
            row["distinct_cases"] = int(subset[distinct_columns].fillna("").drop_duplicates().shape[0])
            examples: list[str] = []
            for _, example in subset[distinct_columns + ["source_row", "entity_id"]].fillna("").drop_duplicates().head(3).iterrows():
                parts = []
                if str(example["source_file"]).strip():
                    location = str(example["source_file"])
                    if str(example["source_row"]).strip():
                        location += f", fila {example['source_row']}"
                    parts.append(location)
                if str(example["original_value"]).strip() and str(example["original_value"]) != "<NA>":
                    parts.append(f"valor: {example['original_value']}")
                elif str(example["entity_id"]).strip():
                    parts.append(f"ID: {example['entity_id']}")
                if parts:
                    examples.append(" · ".join(parts))
            row["examples"] = examples
        return rows

    def overview(self) -> dict[str, Any]:
        """Resume hallazgos y situaciones por estado visible."""
        frame = self.to_frame()
        rules = self.rule_counts()
        statuses = (
            "Excluido por inconsistencia",
            "Procesado con limitación",
            "Resuelto automáticamente",
            "Excluido por criterios de análisis",
            "Configuración aplicada",
        )
        affected = {
            status: int(sum(item["count"] for item in rules if item["status"] == status))
            for status in statuses
        }
        situations = {
            status: int(sum(1 for item in rules if item["status"] == status))
            for status in statuses
        }
        source_rows = frame.loc[
            frame["source_file"].astype("string").str.strip().ne("") & frame["source_row"].notna(),
            ["source_file", "source_row"],
        ].drop_duplicates()
        return {
            "affected_records": int(sum(item["count"] for item in rules)),
            "affected_source_rows": int(len(source_rows)),
            "situation_types": len(rules),
            "affected_by_status": affected,
            "situations_by_status": situations,
        }

    def to_user_frame(self) -> pd.DataFrame:
        """Convierte el detalle técnico en una tabla orientada al usuario."""
        frame = self.to_frame()
        columns = [
            "Estado", "Situación", "Descripción", "Resultado en el procesamiento", "Recomendación", "Archivo",
            "Fila", "Identificador", "Campo", "Valor original", "Acción técnica",
        ]
        if frame.empty:
            return pd.DataFrame(columns=columns)
        metadata = frame["rule"].map(lambda rule: QUALITY_RULES.get(str(rule), {}))
        result = pd.DataFrame({
            "Estado": metadata.map(lambda item: item.get("status", "Situación no clasificada")),
            "Situación": metadata.map(lambda item: item.get("title", "Incidencia de calidad")),
            "Descripción": metadata.map(lambda item: item.get("description", "Revise el detalle técnico de la incidencia.")),
            "Resultado en el procesamiento": metadata.map(lambda item: item.get("result", "La regla fue aplicada durante el procesamiento.")),
            "Recomendación": metadata.map(lambda item: item.get("recommendation", "Valide el registro en los archivos de entrada.")),
            "Archivo": frame["source_file"],
            "Fila": frame["source_row"].astype("Int64"),
            "Identificador": frame["entity_id"],
            "Campo": frame["field"],
            "Valor original": frame["original_value"],
            "Acción técnica": frame["action"],
        })
        return result[columns]

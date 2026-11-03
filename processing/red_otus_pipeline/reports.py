"""Genera los reportes legibles de proyectos y calidad de datos."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd


STATUS_CLASS = {
    "Excluido por inconsistencia": "excluded",
    "Procesado con limitación": "limited",
    "Resuelto automáticamente": "resolved",
    "Excluido por criterios de análisis": "excluded",
    "Configuración aplicada": "configured",
    # Alias para poder abrir reportes construidos con metadatos históricos.
    "Requiere revisión": "excluded",
    "Exclusión informativa": "excluded",
}


def project_summary(
    observations: pd.DataFrame,
    deployments: pd.DataFrame,
    projects: pd.DataFrame,
) -> pd.DataFrame:
    """Resume observaciones, eventos, especies y cámaras por proyecto."""
    observation_stats = observations.groupby("project_id", as_index=False).agg(
        observaciones=("project_id", "size"), eventos=("subproject_name", "nunique"), especies=("sp_binomial", "nunique")
    )
    deployment_stats = deployments.groupby("project_id", as_index=False).agg(
        camaras=("deployment_key", "nunique"),
        corporacion=("Corporacion", lambda values: ", ".join(sorted(set(values.dropna().astype(str))))),
    )
    columns = [column for column in ("project_id", "project_short_name", "project_name") if column in projects]
    result = projects[columns].drop_duplicates("project_id").merge(observation_stats, on="project_id", how="left")
    result = result.merge(deployment_stats, on="project_id", how="left")
    preferred_name = result.get("project_short_name", pd.Series(index=result.index, dtype="string"))
    if "project_name" in result:
        preferred_name = preferred_name.fillna(result["project_name"])
    result.insert(1, "proyecto", preferred_name.fillna("Sin nombre"))
    result = result.drop(columns=[column for column in ("project_short_name", "project_name") if column in result])
    for column in ("observaciones", "eventos", "especies", "camaras"):
        result[column] = result[column].fillna(0).astype(int)
    return result.sort_values(["observaciones", "project_id"], ascending=[False, True]).reset_index(drop=True)


def _badge(status: str) -> str:
    css_class = STATUS_CLASS.get(status, "review")
    return f"<span class='badge {css_class}'>{escape(status)}</span>"


def _examples(values: list[str]) -> str:
    if not values:
        return "<span class='muted'>Sin ejemplo disponible</span>"
    return "<ul class='examples'>" + "".join(f"<li>{escape(str(value))}</li>" for value in values) + "</ul>"


def write_quality_html(
    path: Path,
    issues: pd.DataFrame,
    counts: dict[str, int],
    rules: list[dict[str, Any]],
    run_id: str,
    overview: dict[str, Any] | None = None,
) -> None:
    """Escribe el reporte HTML navegable de calidad de datos."""
    overview = overview or {}
    affected_by_status = overview.get("affected_by_status", {})
    situations_by_status = overview.get("situations_by_status", {})
    rule_rows = "".join(
        "<tr>"
        f"<td>{_badge(str(rule.get('status', 'Situación no clasificada')))}</td>"
        f"<td>{escape(str(rule.get('title', rule['rule'])))}</td>"
        f"<td class='number'>{int(rule['count']):,}</td>"
        f"<td class='number'>{int(rule.get('distinct_cases', rule['count'])):,}</td>"
        f"<td>{escape(str(rule.get('description', '')))}</td>"
        f"<td>{escape(str(rule.get('result', '')))}</td>"
        f"<td>{_examples(rule.get('examples', []))}</td>"
        f"<td>{escape(str(rule.get('recommendation', '')))}</td>"
        "</tr>" for rule in rules
    ) or "<tr><td colspan='8'>No se identificaron situaciones de calidad.</td></tr>"

    columns = list(issues.columns)
    if len(issues) > 1000 and "Situación" in issues:
        per_situation = max(1, 1000 // max(1, issues["Situación"].nunique()))
        visible_issues = issues.groupby("Situación", sort=False, group_keys=False).head(per_situation)
        if len(visible_issues) < 1000:
            remaining = issues.drop(index=visible_issues.index).head(1000 - len(visible_issues))
            visible_issues = pd.concat([visible_issues, remaining], ignore_index=True)
    else:
        visible_issues = issues.head(1000)
    status_column = "Estado" if "Estado" in columns else "Nivel" if "Nivel" in columns else None
    level_index = columns.index(status_column) if status_column else None
    situation_index = columns.index("Situación") if "Situación" in columns else None
    detail_rows_list: list[str] = []
    for row in visible_issues.itertuples(index=False, name=None):
        level = str(row[level_index]) if level_index is not None else ""
        situation = str(row[situation_index]) if situation_index is not None else ""
        cells = []
        searchable_values: list[str] = []
        for index, value in enumerate(row):
            text = "" if pd.isna(value) else str(value)
            searchable_values.append(text)
            cells.append(f"<td>{_badge(text) if index == level_index else escape(text)}</td>")
        search_text = " ".join(searchable_values)
        detail_rows_list.append(
            f"<tr data-level='{escape(level)}' data-situation='{escape(situation)}' "
            f"data-search='{escape(search_text)}'>{''.join(cells)}</tr>"
        )
    detail_rows = "".join(detail_rows_list) or f"<tr><td colspan='{max(1, len(columns))}'>No se identificaron situaciones de calidad.</td></tr>"
    headers = "".join(f"<th>{escape(str(column))}</th>" for column in columns)

    filter_options_parts: list[str] = []
    if status_column and "Situación" in issues:
        pairs = issues[[status_column, "Situación"]].fillna("").drop_duplicates()
        status_order = [status for status in STATUS_CLASS if status in set(pairs[status_column])]
        status_order.extend(sorted(set(pairs[status_column]).difference(status_order)))
        for status in status_order:
            if not str(status).strip():
                continue
            situations = sorted(
                value for value in pairs.loc[pairs[status_column].eq(status), "Situación"].astype(str).unique()
                if value.strip()
            )
            options = [
                f"<option value='{escape(str(status))}|||'>Todas las situaciones de este estado</option>"
            ]
            options.extend(
                f"<option value='{escape(str(status))}|||{escape(situation)}'>{escape(situation)}</option>"
                for situation in situations
            )
            filter_options_parts.append(
                f"<optgroup label='{escape(str(status))}'>{''.join(options)}</optgroup>"
            )
    filter_options = "".join(filter_options_parts)

    def count_map(frame: pd.DataFrame) -> dict[str, int]:
        result = {"": int(len(frame))}
        if status_column and status_column in frame and "Situación" in frame:
            grouped_status = frame.groupby(status_column, dropna=False).size()
            for status, count in grouped_status.items():
                result[f"{status}|||" ] = int(count)
            grouped_pair = frame.groupby([status_column, "Situación"], dropna=False).size()
            for (status, situation), count in grouped_pair.items():
                result[f"{status}|||{situation}"] = int(count)
        return result

    total_counts_json = json.dumps(count_map(issues), ensure_ascii=False)
    sample_counts_json = json.dumps(count_map(visible_issues), ensure_ascii=False)

    def card(status: str, label: str) -> str:
        situations = int(situations_by_status.get(status, 0))
        affected = int(affected_by_status.get(status, 0))
        return f"<div class='card'><div class='value'>{situations:,}</div><div>{escape(label)}</div><div class='card-note'>{affected:,} hallazgos registrados</div></div>"

    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reporte de calidad de datos - Red OTUS</title><style>
body{{font-family:'Segoe UI',Arial,sans-serif;margin:0;background:#f3f7fa;color:#203b63}}
header{{background:#203b63;color:white;padding:28px 5%}} main{{padding:24px 5% 48px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:18px 0}}
.card,section,.notice{{background:white;border:1px solid #d9e3ec;border-radius:10px;padding:18px;box-shadow:0 3px 12px #17324d12}}
.notice{{margin:18px 0;border-left:5px solid #159bd3;box-shadow:none}} .value{{font-size:26px;font-weight:700;color:#159bd3}}
.card-note,.muted{{color:#607489;font-size:12px;margin-top:5px}} h2{{font-size:19px;margin-top:10px}} .table-wrap{{overflow:auto}}
table{{border-collapse:collapse;width:100%;font-size:13px}} th{{background:#329bd3;color:white;text-align:left;position:sticky;top:0}}
th,td{{border:1px solid #d9e3ec;padding:9px;vertical-align:top}} tr:nth-child(even){{background:#f7fafc}} .number{{text-align:right;white-space:nowrap}}
.badge{{display:inline-block;padding:4px 8px;border-radius:12px;white-space:nowrap;font-weight:600}} .badge.review{{background:#e1f3fb;color:#0b628a}}
.badge.limited{{background:#fff1cf;color:#805b00}} .badge.resolved{{background:#e4f5eb;color:#167242}} .badge.excluded{{background:#e1f3fb;color:#0b628a}} .badge.configured{{background:#eee8fb;color:#5f3aa5}}
.examples{{margin:0;padding-left:17px}} .examples li{{margin-bottom:4px}} .controls{{display:flex;align-items:flex-end;gap:12px;margin:14px 0;flex-wrap:wrap}}
.control{{display:flex;flex-direction:column;gap:5px;min-width:260px}} .control.search{{flex:1 1 320px}}
select,input[type=search]{{padding:8px 10px;border:1px solid #b9cad8;border-radius:5px;background:white;color:#203b63;font:inherit}}
input[type=search]{{width:100%;box-sizing:border-box}} #visibleCount{{flex-basis:100%;font-size:13px}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body><header><h1>Reporte de calidad de datos</h1><p>Ejecución {escape(run_id)}</p></header><main>
<div class="notice"><strong>Cómo interpretar este reporte.</strong> Se registraron <strong>{int(overview.get('affected_records', counts.get('total', 0))):,} hallazgos</strong>, agrupados en <strong>{int(overview.get('situation_types', len(rules))):,} tipos de situación</strong> y asociados a {int(overview.get('affected_source_rows', 0)):,} filas de origen identificables. Una misma fila puede aparecer en más de una situación, por lo que los hallazgos no equivalen necesariamente al número de observaciones únicas. Cada estado indica si el dato fue excluido, se conservó con alguna limitación, se resolvió automáticamente o quedó fuera por un criterio esperado del análisis.</div>
<div class="cards"><div class="card"><div class="value">{int(overview.get('situation_types', len(rules))):,}</div><div>Tipos de situación</div><div class="card-note">{int(overview.get('affected_records', counts.get('total', 0))):,} hallazgos registrados</div></div>
{card('Excluido por inconsistencia', 'Situaciones excluidas por inconsistencia')}{card('Procesado con limitación', 'Situaciones procesadas con limitación')}{card('Resuelto automáticamente', 'Situaciones resueltas automáticamente')}{card('Excluido por criterios de análisis', 'Exclusiones por criterios de análisis')}</div>
<section><h2>Resumen y acciones sugeridas</h2><div class="table-wrap"><table><thead><tr><th>Estado</th><th>Situación</th><th>Registros afectados</th><th>Casos distintos</th><th>Qué significa</th><th>Resultado</th><th>Ejemplos</th><th>Qué puede revisar</th></tr></thead><tbody>{rule_rows}</tbody></table></div></section>
<section><h2>Detalle de registros</h2><p class="muted">Esta tabla presenta una muestra estratificada de {len(visible_issues):,} filas, seleccionada a partir de {len(issues):,} hallazgos del detalle completo. Se reserva espacio para cada situación con el fin de mostrar ejemplos variados; por ello, la cantidad visible no representa la proporción real de cada situación. Los archivos CSV y Parquet contienen la totalidad del detalle.</p><div class="controls"><label class="control" for="statusSituationFilter"><strong>Filtrar por estado y situación</strong><select id="statusSituationFilter"><option value="">Todos los estados y situaciones</option>{filter_options}</select></label><label class="control search" for="detailSearch"><strong>Buscar en la muestra visible</strong><input id="detailSearch" type="search" placeholder="Escriba archivo, identificador, campo, valor o texto…"></label><span id="visibleCount" class="muted" aria-live="polite"></span></div><div class="table-wrap"><table id="detailTable"><thead><tr>{headers}</tr></thead><tbody>{detail_rows}</tbody></table></div></section>
</main><script>
const filter=document.getElementById('statusSituationFilter');
const search=document.getElementById('detailSearch');
const rows=[...document.querySelectorAll('#detailTable tbody tr[data-level]')];
const counter=document.getElementById('visibleCount');
const totalCounts={total_counts_json};
const sampleCounts={sample_counts_json};
const normalize=value=>(value||'').toLocaleLowerCase('es-CO').normalize('NFD').replace(/[\u0300-\u036f]/g,'');
function applyFilter(){{
  const [selectedLevel='',selectedSituation='']=filter.value.split('|||');
  const query=normalize(search.value.trim());
  let visible=0;
  rows.forEach(row=>{{
    const stateMatches=!selectedLevel||row.dataset.level===selectedLevel;
    const situationMatches=!selectedSituation||row.dataset.situation===selectedSituation;
    const searchMatches=!query||normalize(row.dataset.search).includes(query);
    const show=stateMatches&&situationMatches&&searchMatches;
    row.style.display=show?'':'none';
    if(show)visible++;
  }});
  const sampleTotal=sampleCounts[filter.value]??sampleCounts['']??rows.length;
  const fullTotal=totalCounts[filter.value]??totalCounts['']??rows.length;
  const suffix=query
    ? ` coinciden con la búsqueda dentro de ${{sampleTotal.toLocaleString('es-CO')}} filas de la muestra`
    : ` visibles en la muestra HTML`;
  counter.textContent=`${{visible.toLocaleString('es-CO')}} filas${{suffix}}. El detalle completo contiene ${{fullTotal.toLocaleString('es-CO')}} registros para este filtro.`;
}}
filter.addEventListener('change',applyFilter);
search.addEventListener('input',applyFilter);
applyFilter();
</script></body></html>"""
    path.write_text(html, encoding="utf-8")

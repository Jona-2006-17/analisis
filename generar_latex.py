"""
generar_latex.py
----------------
Agrega esta función al final de tu script principal.
Llámala así al final del script:

    from generar_latex import generar_latex
    generar_latex(reporte, start_day=start_day, end_day=end_day)

Requisito: pip install jinja2
"""

import calendar
import os
from jinja2 import Environment, FileSystemLoader


MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def generar_latex(reporte: dict, start_day: int = 1, end_day: int = None,
                  template_path: str = "reporte_mensual.tex.j2", carpeta = str) -> str:
    """
    Recibe el diccionario `reporte` y genera el archivo .tex relleno.

    Parámetros:
        reporte       : el diccionario completo generado por el script de análisis
        start_day     : día de inicio del período (por defecto 1)
        end_day       : día de fin del período (por defecto último día del mes)
        template_path : ruta al archivo .j2 (por defecto en el mismo directorio)

    Retorna:
        Ruta del archivo .tex generado
    """

    meta      = reporte["meta"]
    anio      = meta["year"]
    mes       = meta["month"]
    mes_nombre = MESES_ES[mes]

    if end_day is None:
        end_day = calendar.monthrange(anio, mes)[1]

    # ── Métrica 1 ─────────────────────────────────────────────────────────────
    promedio_diario = reporte["promedio_diario_conversaciones"]["datos"]
    meta_filtrado   = reporte["promedio_diario_conversaciones"]["metadatos"]
    dias_semana     = [f["dia"] for f in promedio_diario]

    # ── Métrica 2 ─────────────────────────────────────────────────────────────
    mensajes_por_hora      = reporte["promedio_mensajes_por_hora_contactos"]["datos"]
    total_mensajes_contacto = reporte["promedio_mensajes_por_hora_contactos"]["metadatos"]["total_mensajes_contacto"]

    # ── Métrica 3 ─────────────────────────────────────────────────────────────
    mensajes_agente_hora = reporte["promedio_mensajes_por_hora_agente"]["datos"]
    nombres_agentes      = reporte["promedio_mensajes_por_hora_agente"]["metadatos"]["agentes"]

    # ── Métrica 4 ─────────────────────────────────────────────────────────────
    primera_respuesta_tabla   = reporte["promedio_primera_respuesta"]["datos"]["tabla"]
    primera_respuesta_legible = reporte["promedio_primera_respuesta"]["datos"]["legible"]["total"]
    # estadisticos viene como {"tiempo_respuesta_minutos": {"count": X, "mean": X, ...}}
    estadisticos_raw = reporte["promedio_primera_respuesta"]["datos"]["estadisticos"]["tiempo_respuesta_minutos"]

    # ── Métrica 5 ─────────────────────────────────────────────────────────────
    primera_resp_agente = reporte["promedio_primera_respuesta_agente"]["datos"]

    # ── Métrica 6 ─────────────────────────────────────────────────────────────
    duracion      = reporte["duracion_conversaciones"]["datos"]
    duracion_meta = reporte["duracion_conversaciones"]["metadatos"]

    # ── Métrica 7 ─────────────────────────────────────────────────────────────
    agendamiento_tabla = reporte["conversion_agendamientos"]["datos"]["tabla"]
    agendamiento_pie   = reporte["conversion_agendamientos"]["datos"]["pie_chart"]
    agendamiento_meta  = reporte["conversion_agendamientos"]["metadatos"]
    porc_agendadas     = round(agendamiento_pie[0]["porcentaje"], 1)

    # ── Métrica 8 ─────────────────────────────────────────────────────────────
    satisfaccion_bot         = reporte["satisfaccion"]["datos"]["bot"]["promedio"]
    satisfaccion_agente      = reporte["satisfaccion"]["datos"]["agente"]["promedio"]
    satisfaccion_resp_bot    = reporte["satisfaccion"]["datos"]["bot"]["total_respuestas"]
    satisfaccion_resp_agente = reporte["satisfaccion"]["datos"]["agente"]["total_respuestas"]

    # ── Configurar Jinja2 ─────────────────────────────────────────────────────
    directorio_base = os.path.dirname(os.path.abspath(__file__))
    env = Environment(
        loader=FileSystemLoader(directorio_base),
        block_start_string="[%",
        block_end_string="%]",
        variable_start_string="[[",
        variable_end_string="]]",
        comment_start_string="[#",
        comment_end_string="#]",
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template  = env.get_template(template_path)

    # ── Renderizar ────────────────────────────────────────────────────────────
    contenido = template.render(
        # Meta
        anio                      = anio,
        mes_nombre                = mes_nombre,
        start_day                 = start_day,
        end_day                   = end_day,
        meta_filtrado             = meta_filtrado,
        # KPIs resumen ejecutivo
        primera_respuesta_legible = primera_respuesta_legible,
        satisfaccion_bot          = satisfaccion_bot,
        satisfaccion_agente       = satisfaccion_agente,
        porc_agendadas            = porc_agendadas,
        # Métrica 1
        promedio_diario           = promedio_diario,
        dias_semana               = dias_semana,
        # Métrica 2
        mensajes_por_hora         = mensajes_por_hora,
        total_mensajes_contacto   = total_mensajes_contacto,
        # Métrica 3
        mensajes_agente_hora      = mensajes_agente_hora,
        nombres_agentes           = nombres_agentes,
        # Métrica 4
        primera_respuesta_tabla   = primera_respuesta_tabla,
        estadisticos              = estadisticos_raw,
        # Métrica 5
        primera_resp_agente       = primera_resp_agente,
        # Métrica 6
        duracion                  = duracion,
        duracion_meta             = duracion_meta,
        # Métrica 7
        agendamiento_tabla        = agendamiento_tabla,
        agendamiento_pie          = agendamiento_pie,
        agendamiento_meta         = agendamiento_meta,
        # Métrica 8
        satisfaccion_resp_bot     = satisfaccion_resp_bot,
        satisfaccion_resp_agente  = satisfaccion_resp_agente,
    )

    # ── Guardar archivo .tex ──────────────────────────────────────────────────
    nombre_archivo = f"reporte/reporte_{mes_nombre.lower()}_{anio}.tex"

    if carpeta is None:
        carpeta = f"reporte_{mes:02d}_{anio}"

    os.makedirs(carpeta, exist_ok=True)
    nombre_archivo = os.path.join(carpeta, f"reporte_{mes_nombre.lower()}_{anio}.tex")
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"✅ Archivo generado: {nombre_archivo}")
    return nombre_archivo

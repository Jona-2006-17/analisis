import pandas as pd
import holidays
import matplotlib
matplotlib.use('Agg')
from generar_latex import generar_latex
from config import engine, year_rp, month_rp, start_day, end_day
from metricas import m1_promedio_diario, m2_promedio_mensajes_por_hora, m3_mensajes_por_hora_agnt, m4_promedio_primera_respuesta, m5_promedio_primera_respuesta_agnt, m6_promedio_duracion_conv, m7_porcentaje_conversion_agendamiento, m8_promedio_satisfaccion, m9_utilizacion_Capacidad
import os

carpeta_reporte = f"reporte_{month_rp:02d}_{year_rp}"
os.makedirs(carpeta_reporte, exist_ok=True)


# Promedio diario de conversaciones 
sentencia = "SELECT * FROM conversations WHERE created_at >= '2025-11-01'"

co_holidays = holidays.Colombia(years=year_rp)
co_holidays_dt = pd.to_datetime(list(co_holidays))

df = pd.read_sql(sentencia, engine)
df['created_at'] = pd.to_datetime(df['created_at'])

df = df[
    (df['created_at'].dt.year == year_rp) & 
    (df['created_at'].dt.month == month_rp) & 
    (df['created_at'].dt.day >= start_day) & 
    (df['created_at'].dt.day <= end_day)
    
]
df = df.sort_values(['id', 'created_at'])
df['holiday'] = df['created_at'].dt.normalize().isin(co_holidays_dt)

contactos = pd.read_sql("SELECT * FROM contacts WHERE name ~ '[A-Za-z]'", engine)
ids_ignorar_contactos = contactos['id'].unique().tolist()

m1_resultado, df_filtrado = m1_promedio_diario.calcular(df, ids_ignorar_contactos)

reporte = {
    "meta": {"year": year_rp, "month": month_rp},
    "promedio_diario_conversaciones": m1_resultado,
}

ids_conversaciones_validas = df_filtrado['id'].unique()

#Promedio mensajes por hora
sentencia_messages = "SELECT * FROM messages WHERE created_at >= '2025-11-01'" 
df_all_messages = pd.read_sql(sentencia_messages, engine)

df_messages = df_all_messages[(df_all_messages['conversation_id'].isin(ids_conversaciones_validas))].copy()
df_messages = df_messages.sort_values(['conversation_id', 'created_at'])


msg_agnts = df_messages[
    (df_messages['sender_type'].notna()) & 
    (df_messages['sender_type'] == 'User') & 
    (df_messages['sender_id'] != 1) & 
    (df_messages['sender_id'] != 11) & 
    (df_messages['sender_id'] != 14) &
    (df_messages['sender_id'] != 9)
].copy()

m2_resultado, tabla_m2 = m2_promedio_mensajes_por_hora.calcular(df_messages)

reporte["promedio_mensajes_por_hora_contactos"] = m2_resultado
m2_promedio_mensajes_por_hora.graficar(tabla_m2, output_path=f"{carpeta_reporte}/heatmap_contactos.png")

# Mensajes por hora de cada agente
m3_resultado, tabla_m3 = m3_mensajes_por_hora_agnt.calcular(msg_agnts)
reporte["promedio_mensajes_por_hora_agente"] = m3_resultado
m3_mensajes_por_hora_agnt.graficar(tabla_m3, output_path=f"{carpeta_reporte}/heatmap_agentes.png")

# Promedio de primera respuesta
reporte["promedio_primera_respuesta"] = m4_promedio_primera_respuesta.calcular(df_filtrado, df_all_messages)

#Promedio primera respuesta por agente
m5_resultado, promedio_agente_sorted = m5_promedio_primera_respuesta_agnt.calcular(df_messages)
reporte["promedio_primera_respuesta_agente"] = m5_resultado
m5_promedio_primera_respuesta_agnt.graficar(promedio_agente_sorted, output_path=f"{carpeta_reporte}/barras_primera_respuesta_agente.png")


#Mediana del tiempo entre mensajes usuario → agente durante conversaciones activas.
#MIRAR DF_ALL_MESAGGES
sentencia_messages_contact_user = "SELECT * FROM messages WHERE created_at >= '2025-11-01'"
df_messages_contact_user = pd.read_sql(sentencia_messages_contact_user, engine)

reporte["duracion_conversaciones"] = m6_promedio_duracion_conv.calcular(df_messages_contact_user, ids_conversaciones_validas)

#Porcentaje de conversaciones agendadas
m7_resultado, cant_agendadas, total_conv = m7_porcentaje_conversion_agendamiento.calcular(df_filtrado)
reporte["conversion_agendamientos"] = m7_resultado
m7_porcentaje_conversion_agendamiento.graficar(cant_agendadas, total_conv, output_path=f"{carpeta_reporte}/torta_agendamientos.png")

#Promedio de satisfaccion
reporte["satisfaccion"] = m8_promedio_satisfaccion.calcular(ids_conversaciones_validas)


#Utilización de Capacidad (%), tiempo de agente en la app por medio del tiempo en que escribe

# reporte["actividad_agentes"] = m9_utilizacion_Capacidad.calcular(df_all_messages, ids_conversaciones_validas)



# print(json.dumps(reporte, indent=4, ensure_ascii=False, default=str))
# with open("reporte.json", "w", encoding="utf-8") as f:
#     json.dump(reporte, f, indent=4, ensure_ascii=False, default=str)

generar_latex(reporte, start_day=start_day, end_day=end_day, carpeta=carpeta_reporte)
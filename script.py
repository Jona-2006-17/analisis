import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import holidays
import re
import json
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns

engine = create_engine("postgresql+psycopg2://intern_new:internpass_new@localhost:5434/intern_db_new")
engine2 = create_engine("postgresql+psycopg2://intern:internpass@localhost:5433/intern_db")

# Promedio diario de conversaciones 
sentencia = "SELECT * FROM conversations WHERE created_at >= '2025-11-01'"

year_rp = 2026
month_rp = 1
start_day = 1
end_day = 30

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
ids_ignorar_contactos = contactos['id'].unique()
ids_ignorar_contactos = ids_ignorar_contactos.tolist()

cantidad_datos_sin_filtrar = len(df)

ids_conversaciones_ignorar = df.loc[df['contact_id'].isin(ids_ignorar_contactos), 'id']

ids_sin_first_reply_created_at = df.loc[df['first_reply_created_at'].isna(), 'id']
ids_conversaciones_ignorar = pd.concat([ids_conversaciones_ignorar, ids_sin_first_reply_created_at]).unique()

cantidad_conversaciones_ignoradas_contactos = df['id'].isin(ids_conversaciones_ignorar).sum()

df = df[~df['id'].isin(ids_conversaciones_ignorar)]

cantidad_conversaciones_festivos = df[df['holiday']]


df = df[~df['holiday']]
cantidad_datos_filtrados = len(df)
df['weekday'] = df['created_at'].dt.weekday
promedios_24_h = (
    df.groupby([df['weekday'], df['created_at'].dt.to_period('D')])
    .size()
    .groupby(level=0)
    .mean()
    .round(2)
)
df_promedios_semanal = promedios_24_h.reset_index()
df_promedios_semanal.columns = ['weekday', 'promedio_conversaciones']
mapa_dias = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    6: "domingo"
}

df_promedios_semanal["dia"] = df_promedios_semanal["weekday"].map(mapa_dias)

df_promedios_semanal = df_promedios_semanal[["dia", "promedio_conversaciones"]]

ids_conversaciones_validas = df['id'].unique()

reporte = {
    "meta": {
        "year": year_rp,
        "month": month_rp,
    },
    "promedio_diario_conversaciones": {
        "metadatos": {
            "total_sin_filtrar": cantidad_datos_sin_filtrar,
            "total_ignorados": int(cantidad_conversaciones_ignoradas_contactos),
            "total_festivos": len(cantidad_conversaciones_festivos),
            "total_filtrado_final": cantidad_datos_filtrados,
        },
        "datos": df_promedios_semanal.to_dict(orient="records")
    }
}

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
df_messages_contact = df_messages[(df_messages['sender_type'].notna()) & (df_messages['sender_type'] != 'User')].copy()

df_messages_contact['created_at'] = df_messages_contact['created_at'].dt.tz_localize('UTC')
df_messages_contact['created_at'] = df_messages_contact['created_at'].dt.tz_convert('America/Bogota')

df_messages_contact['weekday'] = df_messages_contact['created_at'].dt.weekday
df_messages_contact['hour'] = df_messages_contact['created_at'].dt.hour
df_messages_contact['date'] = df_messages_contact['created_at'].dt.date


conteo_dias = (
    df_messages_contact.groupby(['weekday', 'date', 'hour'])
    .size()
    .reset_index(name='conteo')
)
promedio_por_hora = (
    conteo_dias
    .groupby(['weekday', 'hour'])['conteo']
    .mean()
    .round(2)
)
promedio_por_hora.head(30)

tabla = promedio_por_hora.unstack(level=0)


tabla = tabla.rename(columns=mapa_dias)

tabla = tabla.reset_index()

tabla = tabla.sort_values("hour")
tabla = tabla.fillna(0)

reporte["promedio_mensajes_por_hora_contactos"] = {
    "metadatos": {
        "total_mensajes_contacto": len(df_messages_contact),
    },
    "datos": tabla.to_dict(orient="records")
}

##
tabla_plot = tabla.set_index('hour')
tabla_plot = tabla_plot[(tabla_plot.index >= 6) & (tabla_plot.index <= 22)]
orden_cols = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
cols_presentes = [c for c in orden_cols if c in tabla_plot.columns]
tabla_plot = tabla_plot[cols_presentes]

fig, ax = plt.subplots(figsize=(16, 4))
sns.heatmap(
    tabla_plot.T,
    cmap="Blues",
    linewidths=1.5,
    annot=True,
    fmt=".0f",
    square=True,
    cbar=True,
    cbar_kws={
        "orientation": "horizontal",
        "location": "top",
        "shrink": 0.4,      # ← más ancho para que coincida con el heatmap
        "aspect": 50,       # ← más delgada
        "pad": 0.02
    },
    ax=ax
)
ax.set_xlabel("Hora del día")
ax.set_ylabel("Día de la semana")
plt.tight_layout()
plt.savefig("reporte/heatmap_contactos.png", dpi=150, bbox_inches='tight')
plt.close(fig)
print("✅ heatmap_contactos.png guardado")

# Mensajes por hora de cada agente
msg_agnts['created_at'] = msg_agnts['created_at'].dt.tz_localize('UTC')
msg_agnts['created_at'] = msg_agnts['created_at'].dt.tz_convert('America/Bogota')
msg_agnts['weekday'] = msg_agnts['created_at'].dt.weekday

msg_agnts['hour'] = msg_agnts['created_at'].dt.hour
msg_agnts['date'] = msg_agnts['created_at'].dt.date

conteo_diario_agente = (
    msg_agnts.groupby(['sender_id', 'weekday', 'date'])
    .size()
    .reset_index(name='mensajes_dia')
)

def horas_laborales(weekday):
    if weekday <= 4:  
        return 8
    elif weekday == 5:
        return 5
    else:            
        return 0
    
conteo_diario_agente['horas_laborales'] = (
    conteo_diario_agente['weekday'].apply(horas_laborales)
)
conteo_diario_agente['mensajes_por_hora'] = (
    conteo_diario_agente['mensajes_dia'] /
    conteo_diario_agente['horas_laborales']
)
promedio_por_dia_agente = (
    conteo_diario_agente
    .groupby(['sender_id', 'weekday'])['mensajes_por_hora']
    .mean()
    .round(2)
    .reset_index()
)

promedio_por_dia_agente["dia"] = (
    promedio_por_dia_agente["weekday"].map(mapa_dias)
)

agentes = {
    6: 'Andres echeverry',
    10: 'Viviana',
    12: 'Jenny',
    13: 'Edwar',
    15: 'Diana',
    16: 'Yoan'
}

promedio_por_dia_agente["sender_id"] = promedio_por_dia_agente["sender_id"].map(agentes).fillna(promedio_por_dia_agente["sender_id"])
promedio_por_dia_agente = promedio_por_dia_agente[['sender_id', 'mensajes_por_hora', 'dia']]
tabla_agentes = promedio_por_dia_agente.pivot(
    index='dia', 
    columns='sender_id', 
    values='mensajes_por_hora'
).fillna(0)

orden_dias = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]
tabla_agentes = tabla_agentes.reindex(orden_dias).reset_index()

reporte["promedio_mensajes_por_hora_agente"] = {
    "metadatos": {
        "total_mensajes_agentes": len(msg_agnts),
        "agentes": list(agentes.values()),
        "criterio_horas_laborales": {
            "lunes_viernes": 8,
            "sabado": 5,
            "domingo": 0
        }
    },
    "datos": tabla_agentes.to_dict(orient="records")
}

tabla_agentes_plot = tabla_agentes.set_index('dia')
tabla_agentes_plot = tabla_agentes_plot.reindex(
    [d for d in ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"] if d in tabla_agentes_plot.index]
)

fig, ax = plt.subplots(figsize=(10, 4))
sns.heatmap(
    tabla_agentes_plot,
    cmap="Oranges",
    linewidths=1.5,
    annot=True,
    fmt=".1f",
    square=True,
    cbar=True,
    ax=ax
)
ax.set_xlabel("Agente")
ax.set_ylabel("Día de la semana")
plt.tight_layout()
plt.savefig("reporte/heatmap_agentes.png", dpi=150, bbox_inches='tight')
plt.close(fig)
print("✅ heatmap_agentes.png guardado")

# Promedio de primera respuesta de conversaciones sin ser iniciadas con plantilla

df_sin_inicio_plantilla = df[~df['cached_label_list'].str.contains('iniciada_con_plantilla', na=False)].copy()

df_sin_inicio_plantilla['created_at'] = df_sin_inicio_plantilla['created_at'].dt.tz_localize('UTC')
df_sin_inicio_plantilla['first_reply_created_at'] = df_sin_inicio_plantilla['first_reply_created_at'].dt.tz_localize('UTC')

df_sin_inicio_plantilla['created_at'] = df_sin_inicio_plantilla['created_at'].dt.tz_convert('America/Bogota')
df_sin_inicio_plantilla['first_reply_created_at'] = df_sin_inicio_plantilla['first_reply_created_at'].dt.tz_convert('America/Bogota')

mismo_dia = df_sin_inicio_plantilla['created_at'].dt.date == df_sin_inicio_plantilla['first_reply_created_at'].dt.date

def calcular_dia_distinto(row):
    inicio = row['created_at']
    primera_respuesta = row['first_reply_created_at']

    segundos = 0

    inicio_laboral_create_at = inicio.replace(hour=7, minute=0, second=0, microsecond=0)
    fin_laboral_created_at = inicio.replace(hour=17, minute=0, second=0, microsecond=0)

    inicio_laboral_first_reply = primera_respuesta.replace(hour=7, minute=0, second=0, microsecond=0)

    if row['created_at'].weekday() == 5:
        inicio_laboral_create_at = inicio.replace(hour=8, minute=0, second=0, microsecond=0)
        fin_laboral_created_at = inicio.replace(hour=12, minute=0, second=0, microsecond=0)
      
    if row['first_reply_created_at'].weekday() == 5:
        inicio_laboral_first_reply = primera_respuesta.replace(hour=8, minute=0, second=0, microsecond=0)

    if inicio >= inicio_laboral_create_at and inicio < fin_laboral_created_at and row['created_at'].weekday() != 6:
        segundos +=(fin_laboral_created_at-inicio).total_seconds()
    
    if primera_respuesta > inicio_laboral_first_reply:
        segundos +=(primera_respuesta - inicio_laboral_first_reply).total_seconds()
    
    return segundos

def calcular_mismo_dia(row):
    inicio = row['created_at']
    primera_respuesta = row['first_reply_created_at']

    segundos = 0

    fin_laboral = inicio.replace(hour=17, minute=0, second=0, microsecond=0)
    inicio_laboral = primera_respuesta.replace(hour=7, minute=0, second=0, microsecond=0)

    if row['created_at'].weekday() == 5:
        fin_laboral = inicio.replace(hour=12, minute=0, second=0, microsecond=0)
        inicio_laboral = primera_respuesta.replace(hour=8, minute=0, second=0, microsecond=0)

    if inicio >= inicio_laboral and inicio < fin_laboral :
        segundos +=(primera_respuesta-inicio).total_seconds()
    
    if inicio < inicio_laboral and primera_respuesta <= fin_laboral:
        segundos +=(primera_respuesta-inicio_laboral).total_seconds()
    
    return max(segundos, 0)
    
df_sin_inicio_plantilla['tiempo_respuesta_segundos'] = np.where(
    mismo_dia,
    df_sin_inicio_plantilla.apply(calcular_mismo_dia, axis=1).round(2),
    df_sin_inicio_plantilla.apply(calcular_dia_distinto, axis=1).round(2)
)

df_sin_inicio_plantilla['tiempo_respuesta_minutos'] = (df_sin_inicio_plantilla['tiempo_respuesta_segundos'] / 60).round(2)
df_sin_inicio_plantilla['tiempo_respuesta_horas'] = (df_sin_inicio_plantilla['tiempo_respuesta_minutos'] / 60).round(2)

promedio_sin_plantilla = df_sin_inicio_plantilla['tiempo_respuesta_minutos'].mean()

df_tiempo_sin_inicio_plantilla = df_sin_inicio_plantilla[['id', 'created_at', 'first_reply_created_at', 'tiempo_respuesta_minutos']]
df_tiempo_sin_inicio_plantilla = df_tiempo_sin_inicio_plantilla.rename(columns={'id':'conversation_id'})

#Promedio primera respuesta de conversaciones iniciadas con plantilla 
ids_conv_iniciadas_plantilla = df.loc[df['cached_label_list'].str.contains('iniciada_con_plantilla', na=False),'id']

df_messages_conv_ini_plantilla = df_all_messages[df_all_messages['conversation_id'].isin(ids_conv_iniciadas_plantilla)].copy()
df_messages_conv_ini_plantilla = df_messages_conv_ini_plantilla.sort_values(['conversation_id', 'created_at'])

primer_mensaje_contacto = df_messages_conv_ini_plantilla[
    (df_messages_conv_ini_plantilla['message_type'] == 0) & 
    (~df_messages_conv_ini_plantilla['content'].isin(['system_resolved', 'system_timeout']))].groupby('conversation_id', as_index=False).first()[['conversation_id', 'created_at']].rename(columns={'created_at': 'created_at_type_0'})

df_merge_tiempo_primer_mensaje_contacto = df_messages_conv_ini_plantilla.merge(primer_mensaje_contacto, on='conversation_id', how='inner')

df_mensajes_agente = df_merge_tiempo_primer_mensaje_contacto[
    (df_merge_tiempo_primer_mensaje_contacto['message_type'] == 1) &
    (df_merge_tiempo_primer_mensaje_contacto['private'] != True) &
    (df_merge_tiempo_primer_mensaje_contacto['created_at'] > df_merge_tiempo_primer_mensaje_contacto['created_at_type_0'])
]

df_primera_respuesta = (df_mensajes_agente.sort_values(['conversation_id', 'created_at']).groupby('conversation_id', as_index=False).first()[['conversation_id', 'created_at']].rename(columns={'created_at': 'first_reply_created_at'}))

df_first_messages = primer_mensaje_contacto.merge(df_primera_respuesta,on='conversation_id',how='left')
df_first_messages = df_first_messages.rename(columns={'created_at_type_0': 'created_at'})

df_first_messages['created_at'] = df_first_messages['created_at'].dt.tz_localize('UTC')
df_first_messages['first_reply_created_at'] = df_first_messages['first_reply_created_at'].dt.tz_localize('UTC')

df_first_messages['created_at'] = df_first_messages['created_at'].dt.tz_convert('America/Bogota')
df_first_messages['first_reply_created_at'] = df_first_messages['first_reply_created_at'].dt.tz_convert('America/Bogota')

mismo_dia_plantilla =  df_first_messages['created_at'].dt.date == df_first_messages['first_reply_created_at'].dt.date
df_first_messages['tiempo_respuesta_minutos'] = np.where(
    mismo_dia_plantilla,
    (df_first_messages.apply(calcular_mismo_dia, axis=1) / 60).round(2),
    (df_first_messages.apply(calcular_dia_distinto, axis=1) / 60).round(2)
)

promedio_con_plantilla = df_first_messages['tiempo_respuesta_minutos'].mean() 


#Promedio primera respuesta general
total_inicio_plantilla = df_first_messages['tiempo_respuesta_minutos'].sum()
cantidad_inicio_plantilla = df_first_messages['tiempo_respuesta_minutos'].count()

total_sin_inicio_plantilla = df_sin_inicio_plantilla['tiempo_respuesta_minutos'].sum()
cantidad_sin_inicio_plantilla = df_sin_inicio_plantilla['tiempo_respuesta_minutos'].count()

promedio_total = ((total_inicio_plantilla + total_sin_inicio_plantilla) / (cantidad_inicio_plantilla + cantidad_sin_inicio_plantilla)).round(2)

df_tiempo_respuesta_unificados = pd.concat([df_tiempo_sin_inicio_plantilla, df_first_messages], ignore_index=True)
detalles = df_tiempo_respuesta_unificados['tiempo_respuesta_minutos'].describe().to_frame()

df_respuesta_plantilla = pd.DataFrame({
    "tipo": [
        "con plantilla",
        "sin plantilla",
        "total"
    ],
    "promedio_minutos": [
        promedio_con_plantilla,
        promedio_sin_plantilla,
        promedio_total
    ]
})
def minutos_a_hhmm(minutos):
    """Convierte minutos decimales a string legible 'Xh Ym' para el reporte."""
    h = int(minutos // 60)
    m = int(minutos % 60)
    return f"{h}h {m}m" if h > 0 else f"{m}m"

reporte["promedio_primera_respuesta"] = {
    "metadatos": {
        "total_conversaciones_sin_plantilla": cantidad_sin_inicio_plantilla,
        "total_conversaciones_con_plantilla": cantidad_inicio_plantilla,
        "total_conversaciones": cantidad_inicio_plantilla + cantidad_sin_inicio_plantilla,
        "horario_laboral": {
            "lunes_viernes": {"inicio": "07:00", "fin": "17:00"},
            "sabado": {"inicio": "08:00", "fin": "12:00"},
            "domingo": "no_laboral"
        }
    },
    "datos": {
        "tabla": df_respuesta_plantilla.to_dict(orient="records"),
        "legible": {
            "con_plantilla": minutos_a_hhmm(promedio_con_plantilla),
            "sin_plantilla": minutos_a_hhmm(promedio_sin_plantilla),
            "total":         minutos_a_hhmm(promedio_total)
        },
        "estadisticos": detalles.to_dict()
    },

}

#Promedio primera respuesta por agente
first_message_contact = (
    df_messages[
        (df_messages['message_type'] == 0) & 
        (~df_messages['content'].isin(['system_resolved', 'system_timeout']))
    ]
    .sort_values('created_at')
    .groupby('conversation_id', as_index=False)
    .first()[['conversation_id', 'created_at']]
    .rename(columns={'created_at': 'created_at_type_0'})
)
df_merge_first_time_contact = df_messages.merge(first_message_contact, on='conversation_id', how='inner')


messages_agent = df_merge_first_time_contact[
    (df_merge_first_time_contact['message_type'] == 1) &
    (df_merge_first_time_contact['sender_id'] != 1) & 
    (df_merge_first_time_contact['sender_id'] != 11) &
    (df_merge_first_time_contact['sender_id'] != 14) &
    (df_merge_first_time_contact['sender_id'] != 9) &
    (df_merge_first_time_contact['private'] != True) &
    (df_merge_first_time_contact['created_at'] > df_merge_first_time_contact['created_at_type_0'])
]


first_message_agent = (
    messages_agent.sort_values(['conversation_id', 'created_at'])
    .groupby('conversation_id', as_index=False)
    .first()[['conversation_id', 'created_at', 'sender_id']]
    .rename(columns={'created_at': 'first_reply_created_at'})
    )

df_merge_firsts = first_message_contact.merge(first_message_agent,on='conversation_id',how='left')

df_merge_firsts = df_merge_firsts.rename(columns={'created_at_type_0': 'created_at'})

df_merge_firsts['created_at'] = df_merge_firsts['created_at'].dt.tz_localize('UTC')
df_merge_firsts['first_reply_created_at'] = df_merge_firsts['first_reply_created_at'].dt.tz_localize('UTC')

df_merge_firsts['created_at'] = df_merge_firsts['created_at'].dt.tz_convert('America/Bogota')
df_merge_firsts['first_reply_created_at'] = df_merge_firsts['first_reply_created_at'].dt.tz_convert('America/Bogota')

same_day = df_merge_firsts['created_at'].dt.date == df_merge_firsts['first_reply_created_at'].dt.date
df_merge_firsts['tiempo_respuesta_minutos'] = np.where(
    same_day,
    (df_merge_firsts.apply(calcular_mismo_dia, axis=1) / 60).round(2),
    (df_merge_firsts.apply(calcular_dia_distinto, axis=1) / 60).round(2)
)
df_merge_firsts.head(20)

promedio_agente = df_merge_firsts.groupby('sender_id')['tiempo_respuesta_minutos'].mean().reset_index(name='promedio_min')


promedio_agente["sender_id"] = promedio_agente["sender_id"].map(agentes).fillna(promedio_agente["sender_id"])
# Agregamos formato legible y ordenamos de menor a mayor (mejor tiempo primero)
promedio_agente_sorted = promedio_agente.sort_values('promedio_min', ascending=True).copy()
promedio_agente_sorted['legible'] = promedio_agente_sorted['promedio_min'].apply(minutos_a_hhmm)

reporte["promedio_primera_respuesta_agente"] = {
    "metadatos": {
        "total_conversaciones_analizadas": len(df_merge_firsts),
        "agentes_excluidos_sistema": [1, 11],
        "nota": "Usa el mismo criterio de horario laboral que promedio_primera_respuesta"
    },
    "datos": promedio_agente_sorted.to_dict(orient="records")
}

# ── Barras verticales primera respuesta por agente → PNG ─────────────────────
colores_agentes = ["#00467F", "#1A6FA8", "#3598D5", "#5BB3E8", "#8ECFF5"]
nombres = promedio_agente_sorted['sender_id'].tolist()
valores = promedio_agente_sorted['promedio_min'].round(1).tolist()
legibles = promedio_agente_sorted['legible'].tolist()
x_pos = range(len(nombres))

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(
    x_pos,
    valores,
    color=colores_agentes[:len(nombres)],
    edgecolor='white',
    width=0.5
)
for bar, legible in zip(bars, legibles):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.5,
        legible,
        ha='center', va='bottom', fontsize=9, fontweight='bold'
    )
ax.set_xticks(list(x_pos))
ax.set_xticklabels(nombres, rotation=15, ha='right')
ax.set_xlabel("Agente", fontsize=10)
ax.set_ylabel("Minutos promedio", fontsize=10)
ax.set_title("Tiempo promedio de primera respuesta por agente", fontsize=11, fontweight='bold')
ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.spines[['top', 'right']].set_visible(False)
plt.tight_layout()
plt.savefig("reporte/barras_primera_respuesta_agente.png", dpi=150, bbox_inches='tight')
plt.close(fig)
print("✅ barras_primera_respuesta_agente.png guardado")

#Mediana del tiempo entre mensajes usuario → agente durante conversaciones activas.
sentencia_messages_contact_user = "SELECT * FROM messages WHERE created_at >= '2025-11-01'"
df_messages_contact_user = pd.read_sql(sentencia_messages_contact_user, engine)

df_messages_contact_user = df_messages_contact_user.sort_values(['conversation_id', 'created_at'])
df_messages_contact_user = df_messages_contact_user[df_messages_contact_user['conversation_id'].isin(ids_conversaciones_validas)]

df_messages_contact_user['prev_message_type'] = df_messages_contact_user.groupby('conversation_id')['message_type'].shift(1)

df_messages_contact_user['is_first_in_block'] = (
    (df_messages_contact_user['message_type'] == 0) &
    (df_messages_contact_user['prev_message_type'] != 0) 
)

mensajes_usuario = df_messages_contact_user[
    df_messages_contact_user['is_first_in_block']
][['conversation_id', 'created_at']].rename(columns={'created_at': 'inicio_bloque'})


mensajes_agente = df_messages_contact_user[
    df_messages_contact_user['message_type'] == 1
][['conversation_id', 'created_at']].rename(columns={'created_at': 'respuesta_agente'})

respuestas = mensajes_usuario.merge(mensajes_agente, on='conversation_id')
respuestas = respuestas[respuestas['respuesta_agente'] > respuestas['inicio_bloque']]
respuestas = (
    respuestas
    .sort_values('respuesta_agente')
    .groupby(['conversation_id', 'inicio_bloque'])
    .first()
    .reset_index()
)

respuestas = respuestas.rename(columns={
    'inicio_bloque': 'created_at',
    'respuesta_agente': 'next_created_at'
})
respuestas['created_at'] = pd.to_datetime(respuestas['created_at'])
respuestas['next_created_at'] = pd.to_datetime(respuestas['next_created_at'])

respuestas['created_at'] = respuestas['created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
respuestas['next_created_at'] = respuestas['next_created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')

mismo_dia_respuestas = respuestas['created_at'].dt.date == respuestas['next_created_at'].dt.date

def medir_dia_distinto(row):
    created_at = row['created_at']

    next_created_at = row['next_created_at']

    inicio_laboral_created_at = created_at.replace(hour=7, minute=0, second=0, microsecond=0)
    fin_laboral_created_at = created_at.replace(hour=17, minute=0, second=0, microsecond=0)

    inicio_laboral_next = next_created_at.replace(hour=7, minute=0, second=0, microsecond=0)
    fin_laboral_next = next_created_at.replace(hour=17, minute=0, second=0, microsecond=0)
    if created_at.weekday() == 5:
        inicio_laboral_created_at = created_at.replace(hour=8, minute=0, second=0, microsecond=0)
        fin_laboral_created_at = created_at.replace(hour=12, minute=0, second=0, microsecond=0)

    if next_created_at.weekday() == 5:
        inicio_laboral_next = next_created_at.replace(hour=8, minute=0, second=0, microsecond=0)
        fin_laboral_next = next_created_at.replace(hour=12, minute=0, second=0, microsecond=0)

    segundos = 0
    if created_at >= inicio_laboral_created_at and created_at <= fin_laboral_created_at and created_at.weekday() != 6:
        segundos += (fin_laboral_created_at - created_at).total_seconds()
    
    if next_created_at >= inicio_laboral_next and next_created_at <= fin_laboral_next:
        segundos += (next_created_at - inicio_laboral_next).total_seconds()

    return max(segundos, 0)

def medir_mismo_dia(row):
    created_at = row['created_at']

    next_created_at = row['next_created_at']

    inicio_laboral_created_at = created_at.replace(hour=7, minute=0, second=0, microsecond=0)
    fin_laboral_created_at = created_at.replace(hour=17, minute=0, second=0, microsecond=0)
    
    segundos = 0
    if created_at >= inicio_laboral_created_at and created_at <= fin_laboral_created_at:
        segundos += (next_created_at - created_at).total_seconds()
    else:
        segundos += (next_created_at - inicio_laboral_created_at).total_seconds()

    return max(segundos, 0)

respuestas['response_time_minutes'] = np.where(
    mismo_dia_respuestas,
    (respuestas.apply(medir_mismo_dia, axis=1) / 60).round(2),
    (respuestas.apply(medir_dia_distinto, axis=1) / 60).round(2)
)
#LO CAMBIE AL PROMEDIO DEL TIEMPO DE RESPUESTA DE UNA CONVERSACION
duracion_conversacion = (
    respuestas
    .groupby('conversation_id')['response_time_minutes']
    .mean()
    .reset_index(name='duracion_total_minutos')
)

promedio_duracion_conversacion = (
    duracion_conversacion['duracion_total_minutos']
    .mean()
    .round(2)
)

mediana_duracion = duracion_conversacion['duracion_total_minutos'].median().round(2)
max_duracion = duracion_conversacion['duracion_total_minutos'].max().round(2)
min_duracion = duracion_conversacion['duracion_total_minutos'].min().round(2)

reporte["duracion_conversaciones"] = {
    "metadatos": {
        "total_conversaciones_analizadas": len(duracion_conversacion),
        "nota": "Duración calculada como suma de tiempos entre mensaje de contacto y respuesta de agente, en horario laboral"
    },
    "datos": {
        "promedio_minutos": promedio_duracion_conversacion,
        "mediana_minutos": mediana_duracion,
        "max_minutos": max_duracion,
        "min_minutos": min_duracion,
        "legible": {
            "promedio": minutos_a_hhmm(promedio_duracion_conversacion),
            "mediana": minutos_a_hhmm(mediana_duracion),
            "max": minutos_a_hhmm(max_duracion),
            "min": minutos_a_hhmm(min_duracion)
        }
    }
}

# Porcentaje conversaciones iniciadas en agendamiento que se agendaron
df_iniciadas_agendamiento = df[
    df['cached_label_list'].str.contains(
        r'(?:^|,)agendamiento(?:$|,)',
        regex=True,
        na=False
    )
]

agendamiento_exitoso = df_iniciadas_agendamiento[df_iniciadas_agendamiento['cached_label_list'].str.contains('agendamiento_exitoso')]

iniciada_agendamiento = df_iniciadas_agendamiento[~df_iniciadas_agendamiento['cached_label_list'].str.contains('agendamiento_exitoso')]

porcentaje_exito_sobre_iniciadas = (len(agendamiento_exitoso) / len(df_iniciadas_agendamiento)) * 100


# Porcentaje de conversaciones no iniciadas en agendamiento que se agendaron
df_no_iniciadas_agendamiento = df[
    ~df['cached_label_list'].str.contains(
        r'(?:^|,)agendamiento(?:$|,)',
        regex=True,
        na=False
    )
]

no_iniciadas_agendamiento_agendadas = df_no_iniciadas_agendamiento[df_no_iniciadas_agendamiento['cached_label_list'].str.contains('agendamiento_exitoso', na=False)]

no_iniciadas_agendamiento_no_agendadas = df_no_iniciadas_agendamiento[~df_no_iniciadas_agendamiento['cached_label_list'].str.contains('agendamiento_exitoso', na=False)]

len(no_iniciadas_agendamiento_no_agendadas)

porcentaje_exito_no_iniciadas = (len(no_iniciadas_agendamiento_agendadas) / len(df_no_iniciadas_agendamiento)) * 100


#Porcentaje de conversaciones agendadas
agendamiento_exitoso = df[df['cached_label_list'].str.contains('agendamiento_exitoso', na=False)]

cant_agendadas = len(agendamiento_exitoso)

porcentaje_total_agendadas = (cant_agendadas / len(df))*100
porcentaje_total_agendadas


df_metricas_agendamiento = pd.DataFrame({
    "metrica": [
        "exito sobre iniciadas",
        "exito sobre no iniciadas",
        "total conversaciones agendadas"
    ],
    "valor": [
        porcentaje_exito_sobre_iniciadas,
        porcentaje_exito_no_iniciadas,
        porcentaje_total_agendadas
    ]
})
reporte["conversion_agendamientos"] = {
    "metadatos": {
        "total_conversaciones": len(df),
        "total_iniciadas_agendamiento": len(df_iniciadas_agendamiento),
        "total_no_iniciadas_agendamiento": len(df_no_iniciadas_agendamiento),
        "total_agendadas_exitosas": cant_agendadas,
    },
    "datos": {
        "tabla": df_metricas_agendamiento.to_dict(orient="records"),
        "pie_chart": [
            {
                "label": "Agendadas exitosas",
                "cantidad": cant_agendadas,
                "porcentaje": round(porcentaje_total_agendadas, 2)
            },
            {
                "label": "No agendadas",
                "cantidad": len(df) - cant_agendadas,
                "porcentaje": round(100 - porcentaje_total_agendadas, 2)
            }
        ]
    }
}


labels_pie = ["Agendadas exitosas", "No agendadas"]
sizes_pie  = [cant_agendadas, len(df) - cant_agendadas]
colores_pie = ["#00467F", "#D2E4F5"]

fig, ax = plt.subplots(figsize=(6, 6))
wedges, texts, autotexts = ax.pie(
    sizes_pie,
    labels=labels_pie,
    colors=colores_pie,
    autopct='%1.1f%%',
    startangle=90,
    wedgeprops={'edgecolor': 'white', 'linewidth': 2},
    textprops={'fontsize': 11}
)
for autotext in autotexts:
    autotext.set_fontsize(12)
    autotext.set_fontweight('bold')
    autotext.set_color('white')
ax.set_title("Conversiones de Agendamiento", fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
plt.savefig("reporte/torta_agendamientos.png", dpi=150, bbox_inches='tight')
plt.close(fig)
print("✅ torta_agendamientos.png guardado")

#Promedio de satisfaccion
sentencia_sessions = "SELECT * FROM sessions WHERE created_at >= '2025-11-01' AND (bot_feedback IS NOT NULL OR agent_feedback IS NOT NULL)"
df_sessions = pd.read_sql(sentencia_sessions, engine2)
df_sessions = df_sessions[df_sessions['conv_id'].isin(ids_conversaciones_validas)]
df_sessions

bot = df_sessions['bot_feedback'].mean().round(1)

agent = df_sessions['agent_feedback'].mean().round(1)

reporte["satisfaccion"] = {
    "metadatos": {
        "total_sesiones_raw": len(pd.read_sql(sentencia_sessions, engine2)),
        "total_sesiones_filtradas": len(df_sessions),
        "escala": "1 a 5",
    },
    "datos": {
        "bot": {
            "promedio": float(bot),
            "total_respuestas": int(df_sessions['bot_feedback'].notna().sum())
        },
        "agente": {
            "promedio": float(agent),
            "total_respuestas": int(df_sessions['agent_feedback'].notna().sum())
        }
    }
}


#Utilización de Capacidad (%), tiempo de agente en la app por medio del tiempo en que escribe
plantilla = [
    '¡Hola! 👋Bienvenido/a al canal exclusivo de asignación de citas de IMÁGENES DIAGNOSTICAS S.A.', 
    'Le acabo de enviar los documentos correspondientes a su solicitud. Por favor, revíselos y cuéntenos si tiene alguna duda. ¿Podemos ayudarle en algo más?', 
    '¡Con gusto! Procederemos a cancelar su cita, por favor, envíanos los siguientes datos para gestionar mejor nuestra agenda y su solicitud.',
    'Recuerde que su lugar de atención es: Centro De Especialistas De Risaralda, Carrera 5 No 18-33,',
    'Para programar su cita, por favor indíquenos los siguientes datos:',
    'Lamentamos la demora en nuestra respuesta. Ayer enfrentamos una contingencia, pero ya estamos atendiendo su solicitud. ¡Gracias por su paciencia!',
    '¡Gracias por elegirnos! 💙 Esperamos poder atenderte nuevamente. Feliz día🌞 En caso de requerir algo adicional, escríbenos en cualquier momento. ¡Estamos para servirte! 😊',
    'Por la complejidad del procedimiento solicitado y su seguridad, requerimos que por favor, nos confirme los siguientes datos:', 
    '📌 Para la solicitud y agendamientos de citas a través del Hospital Universitario San Jorge',
    '📌 Para la solicitud y agendamientos de exámenes de Hemodinamia, agradecemos que por favor nos contacte a través del siguiente WhatsApp 3128345850.',
    'nuestros horarios de atención son de lunes a viernes de 7:00 a.m a 5:00 p.m sabados de 8:00 a.m a 12:00 pm domingos y festivos cerrado',
    'IMÁGENES DIAGNÓSTICAS S.A. 😊 agradece su comunicación y el interés en nuestros servicios.',
    '⌛ "Agradecemos su paciencia. Actualmente estamos recibiendo un volumen de usuarios mayor al habitual, por lo que estamos atendiendo los mensajes por orden de llegada.',
    'Nos permitimos informar que, para la solicitud y consulta de sus resultados',
    '¡Con gusto! Procederemos a reprogramar su cita, por favor, envíanos los siguientes datos para gestionar mejor nuestra agenda y su solicitud.'     
]

df_messages_agent = df_all_messages[(df_all_messages['conversation_id'].isin(ids_conversaciones_validas))].copy()
df_messages_agent = df_messages_agent[
    ((df_messages_agent['created_at'].dt.weekday != 6) & (df_messages_agent['created_at'].dt.weekday != 5) & (df_messages_agent['created_at'].dt.hour >=12) & (df_messages_agent['created_at'].dt.hour <=22)) | (
        (df_messages_agent['created_at'].dt.weekday == 5) &
        (df_messages_agent['created_at'].dt.hour >= 13) &
        (df_messages_agent['created_at'].dt.hour <= 17)
    )
]

df_messages_agent = df_messages_agent[(df_messages_agent['sender_type'] == 'User') & (df_messages_agent['sender_id'] != 1)  & (df_messages_agent['sender_id'] != 11)]

df_messages_agent = df_messages_agent.sort_values(['conversation_id', 'created_at'])

ppm = 40        

df_messages_agent['cantidad_palabras'] = df_messages_agent['content'].fillna("").str.split().str.len()

df_messages_agent['tiempo_minutos_mensaje'] = (df_messages_agent['cantidad_palabras'] / ppm).round(2)

df_messages_agent['created_at'] = pd.to_datetime(df_messages_agent['created_at'])

df_messages_agent['content'] = df_messages_agent['content'].astype(str)

plantillas_escaped = [re.escape(p) for p in plantilla] 

patron = "|".join(plantillas_escaped)
df_messages_agent = df_messages_agent[~df_messages_agent['content'].str.contains(patron, na=False)]

cantidad_minutos_diarios = (
    df_messages_agent
    .groupby([
        df_messages_agent['created_at'].dt.date, 
        'sender_id'
    ])['tiempo_minutos_mensaje'].sum().reset_index(name="minutos")
)


cantidad_minutos_diarios["sender_id"] = cantidad_minutos_diarios["sender_id"].map(agentes).fillna(cantidad_minutos_diarios["sender_id"])

# Pivotamos para tener la tabla heatmap lista: agentes como columnas, días del mes como filas
tabla_actividad = cantidad_minutos_diarios.pivot(
    index='created_at',
    columns='sender_id',
    values='minutos'
).fillna(0).reset_index()

tabla_actividad['created_at'] = tabla_actividad['created_at'].astype(str)

# reporte["actividad_agentes"] = {
#     "metadatos": {
#         "total_mensajes_analizados": len(df_messages_agent),
#         "ppm_utilizado": ppm,
#         "plantillas_excluidas": len(plantilla),
#         "filtro_horario": {
#             "lunes_viernes": "fuera de horario laboral (12:00 - 22:00)",
#             "sabado": "13:00 - 17:00",
#             "domingo": "excluido"
#         },
#         "agentes": list(agentes.values()),
#         "nota": "Tiempo estimado basado en palabras escritas a 40 ppm, excluyendo mensajes de plantilla"
#     },
#     "datos": tabla_actividad.to_dict(orient="records")
# }


# print(json.dumps(reporte, indent=4, ensure_ascii=False, default=str))

# with open("reporte.json", "w", encoding="utf-8") as f:
#     json.dump(reporte, f, indent=4, ensure_ascii=False, default=str)

from generar_latex import generar_latex

generar_latex(reporte, start_day=start_day, end_day=end_day)
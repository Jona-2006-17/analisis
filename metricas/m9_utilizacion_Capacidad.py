import re
import pandas as pd
from config import agentes, plantilla, ppm


def calcular(df_all_messages: pd.DataFrame, ids_conversaciones_validas):
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

    return {
        "metadatos": {
            "total_mensajes_analizados": len(df_messages_agent),
            "ppm_utilizado": ppm,
            "plantillas_excluidas": len(plantilla),
            "filtro_horario": {
                "lunes_viernes": "fuera de horario laboral (12:00 - 22:00)",
                "sabado":        "13:00 - 17:00",
                "domingo":       "excluido"
            },
            "agentes": list(agentes.values()),
            "nota": "Tiempo estimado basado en palabras escritas a 40 ppm, excluyendo mensajes de plantilla"
        },
        "datos": tabla_actividad.to_dict(orient="records")
    }
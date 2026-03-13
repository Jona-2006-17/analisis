import pandas as pd
import numpy as np 
from metricas.m4_promedio_primera_respuesta import minutos_a_hhmm


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

def calcular(df_messages_contact_user: pd.DataFrame, ids_conversaciones_validas):

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
    respuestas['created_at'] = pd.to_datetime(respuestas['created_at']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    respuestas['next_created_at'] = pd.to_datetime(respuestas['next_created_at']).dt.tz_localize('UTC').dt.tz_convert('America/Bogota')


    mismo_dia_respuestas = respuestas['created_at'].dt.date == respuestas['next_created_at'].dt.date

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

    promedio_duracion_conversacion = (duracion_conversacion['duracion_total_minutos'].mean().round(2))
    mediana_duracion = duracion_conversacion['duracion_total_minutos'].median().round(2)
    max_duracion = duracion_conversacion['duracion_total_minutos'].max().round(2)
    min_duracion = duracion_conversacion['duracion_total_minutos'].min().round(2)

    return {
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

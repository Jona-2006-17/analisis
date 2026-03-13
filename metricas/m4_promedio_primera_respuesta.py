import pandas as pd
import numpy as np

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

def minutos_a_hhmm(minutos):
    """Convierte minutos decimales a string legible 'Xh Ym' para el reporte."""
    h = int(minutos // 60)
    m = int(minutos % 60)
    return f"{h}h {m}m" if h > 0 else f"{m}m"

def aplicar_tiempo(df):
    mismo_dia = df['created_at'].dt.date == df['first_reply_created_at'].dt.date
    return np.where(
        mismo_dia,
        (df.apply(calcular_mismo_dia, axis=1) / 60).round(2),
        (df.apply(calcular_dia_distinto, axis=1) / 60).round(2)
    )

def calcular(df: pd.DataFrame, df_all_messages: pd.DataFrame):
    df_sin_inicio_plantilla = df[~df['cached_label_list'].str.contains('iniciada_con_plantilla', na=False)].copy()

    df_sin_inicio_plantilla['created_at'] = df_sin_inicio_plantilla['created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    df_sin_inicio_plantilla['first_reply_created_at'] = df_sin_inicio_plantilla['first_reply_created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')

    df_sin_inicio_plantilla['tiempo_respuesta_segundos'] = np.where(
        df_sin_inicio_plantilla['created_at'].dt.date == df_sin_inicio_plantilla['first_reply_created_at'].dt.date,
        df_sin_inicio_plantilla.apply(calcular_mismo_dia, axis=1).round(2),
        df_sin_inicio_plantilla.apply(calcular_dia_distinto, axis=1).round(2)
    )
    df_sin_inicio_plantilla['tiempo_respuesta_minutos'] = (df_sin_inicio_plantilla['tiempo_respuesta_segundos'] / 60).round(2)
    df_sin_inicio_plantilla['tiempo_respuesta_horas'] = (df_sin_inicio_plantilla['tiempo_respuesta_minutos'] / 60).round(2)

    promedio_sin_plantilla = df_sin_inicio_plantilla['tiempo_respuesta_minutos'].mean()

    df_tiempo_sin_inicio_plantilla = df_sin_inicio_plantilla[['id', 'created_at', 'first_reply_created_at', 'tiempo_respuesta_minutos']].rename(columns={'id':'conversation_id'})


    ##
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

    df_first_messages['created_at'] = df_first_messages['created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    df_first_messages['first_reply_created_at'] = df_first_messages['first_reply_created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    df_first_messages['tiempo_respuesta_minutos'] = aplicar_tiempo(df_first_messages)
    promedio_con_plantilla = df_first_messages['tiempo_respuesta_minutos'].mean() 

    ##
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

    return {
        "metadatos": {
            "total_conversaciones_sin_plantilla": cantidad_sin_inicio_plantilla,
            "total_conversaciones_con_plantilla": cantidad_inicio_plantilla,
            "total_conversaciones": cantidad_inicio_plantilla + cantidad_sin_inicio_plantilla,
            "horario_laboral": {
                "lunes_viernes": {"inicio": "07:00", "fin": "17:00"},
                "sabado":        {"inicio": "08:00", "fin": "12:00"},
                "domingo":       "no_laboral"
            }
        },
        "datos": {
            "tabla":       df_respuesta_plantilla.to_dict(orient="records"),
            "legible": {
                "con_plantilla": minutos_a_hhmm(promedio_con_plantilla),
                "sin_plantilla": minutos_a_hhmm(promedio_sin_plantilla),
                "total":         minutos_a_hhmm(promedio_total)
            },
            "estadisticos": detalles.to_dict()
        },
    }

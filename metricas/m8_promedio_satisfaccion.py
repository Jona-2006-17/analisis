import pandas as pd
from config import engine2


def calcular(ids_conversaciones_validas):
    sentencia_sessions = "SELECT * FROM sessions WHERE created_at >= '2025-11-01' AND (bot_feedback IS NOT NULL OR agent_feedback IS NOT NULL)"
    df_sessions = pd.read_sql(sentencia_sessions, engine2)
    df_sessions = df_sessions[df_sessions['conv_id'].isin(ids_conversaciones_validas)]

    bot = df_sessions['bot_feedback'].mean().round(1)

    agent = df_sessions['agent_feedback'].mean().round(1)

    return {
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
import pandas as pd
from config import mapa_dias

def calcular(df: pd.DataFrame, ids_ignorar_contactos: list):
    cantidad_datos_sin_filtrar = len(df)

    ids_conversaciones_ignorar = df.loc[df['contact_id'].isin(ids_ignorar_contactos), 'id']
    ids_sin_first_reply_created_at = df.loc[df['first_reply_created_at'].isna(), 'id']
    ids_conversaciones_ignorar = pd.concat([ids_conversaciones_ignorar, ids_sin_first_reply_created_at]).unique()

    cantidad_conversaciones_ignoradas_contactos = df['id'].isin(ids_conversaciones_ignorar).sum()
    df = df[~df['id'].isin(ids_conversaciones_ignorar)]

    cantidad_conversaciones_festivos = len(df[df['holiday']])
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
    df_promedios_semanal["dia"] = df_promedios_semanal["weekday"].map(mapa_dias)
    df_promedios_semanal = df_promedios_semanal[["dia", "promedio_conversaciones"]]

    

    return {
        "metadatos": {
                "total_sin_filtrar": cantidad_datos_sin_filtrar,
                "total_ignorados": int(cantidad_conversaciones_ignoradas_contactos),
                "total_festivos": cantidad_conversaciones_festivos,
                "total_filtrado_final": cantidad_datos_filtrados,
            },
        "datos": df_promedios_semanal.to_dict(orient="records")
    }, df
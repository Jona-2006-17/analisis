import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from config import mapa_dias

def calcular(df_messages: pd.DataFrame):
    df_messages_contact = df_messages[(df_messages['sender_type'].notna()) & (df_messages['sender_type'] != 'User')].copy()

    df_messages_contact['created_at'] = df_messages_contact['created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')

    df_messages_contact['weekday'] = df_messages_contact['created_at'].dt.weekday
    df_messages_contact['hour'] = df_messages_contact['created_at'].dt.hour
    df_messages_contact['date'] = df_messages_contact['created_at'].dt.date


    conteo_dias = (
        df_messages_contact.groupby(['weekday', 'date', 'hour'])
        .size()
        .reset_index(name='conteo')
    )
    promedio_por_hora = (
        conteo_dias.groupby(['weekday', 'hour'])['conteo']
        .mean()
        .round(2)
    )

    tabla = promedio_por_hora.unstack(level=0)
    tabla = tabla.rename(columns=mapa_dias)
    tabla = tabla.reset_index().sort_values("hour").fillna(0)

    return {
        "metadatos": {"total_mensajes_contacto": len(df_messages_contact)},
        "datos": tabla.to_dict(orient="records")
    }, tabla

def graficar(tabla: pd.DataFrame, output_path: str = "reporte/heatmap_contactos.png"):
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
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("✅ heatmap_contactos.png guardado")
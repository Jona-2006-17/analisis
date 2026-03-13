import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from config import mapa_dias, agentes
def horas_laborales(weekday):
        if weekday <= 4:  
            return 8
        elif weekday == 5:
            return 5
        else:            
            return 0



def calcular(msg_agnts: pd.DataFrame):

    msg_agnts['created_at'] = msg_agnts['created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    msg_agnts['weekday'] = msg_agnts['created_at'].dt.weekday
    msg_agnts['hour'] = msg_agnts['created_at'].dt.hour
    msg_agnts['date'] = msg_agnts['created_at'].dt.date

    conteo_diario_agente = (
        msg_agnts.groupby(['sender_id', 'weekday', 'date'])
        .size()
        .reset_index(name='mensajes_dia')
    )


    conteo_diario_agente['horas_laborales'] = (
        conteo_diario_agente['weekday'].apply(horas_laborales)
    )
    conteo_diario_agente['mensajes_por_hora'] = (
        conteo_diario_agente['mensajes_dia'] / conteo_diario_agente['horas_laborales']
    )

    promedio_por_dia_agente = (
        conteo_diario_agente
        .groupby(['sender_id', 'weekday'])['mensajes_por_hora']
        .mean()
        .round(2)
        .reset_index()
    )

    promedio_por_dia_agente["dia"] = promedio_por_dia_agente["weekday"].map(mapa_dias)

    promedio_por_dia_agente["sender_id"] = promedio_por_dia_agente["sender_id"].map(agentes).fillna(promedio_por_dia_agente["sender_id"])
    promedio_por_dia_agente = promedio_por_dia_agente[['sender_id', 'mensajes_por_hora', 'dia']]

    tabla_agentes = promedio_por_dia_agente.pivot(
        index='dia', columns='sender_id', values='mensajes_por_hora'
    ).fillna(0)

    orden_dias = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]
    tabla_agentes = tabla_agentes.reindex(orden_dias).reset_index()

    return {
        "metadatos": {
            "total_mensajes_agentes": len(msg_agnts),
            "agentes": list(agentes.values()),
            "criterio_horas_laborales": {"lunes_viernes": 8, "sabado": 5, "domingo": 0}
        },
        "datos": tabla_agentes.to_dict(orient="records")
    }, tabla_agentes


def graficar(tabla_agentes: pd.DataFrame, output_path: str):
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
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("✅ heatmap_agentes.png guardado")
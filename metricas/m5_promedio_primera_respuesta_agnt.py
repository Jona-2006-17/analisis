import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from metricas.m4_promedio_primera_respuesta import calcular_mismo_dia, calcular_dia_distinto, minutos_a_hhmm

from config import agentes, ids_agentes_ignorar


def calcular(df_messages: pd.DataFrame):
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
        (~df_merge_first_time_contact['sender_id'].isin(ids_agentes_ignorar)) & 
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

    df_merge_firsts['created_at'] = df_merge_firsts['created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')
    df_merge_firsts['first_reply_created_at'] = df_merge_firsts['first_reply_created_at'].dt.tz_localize('UTC').dt.tz_convert('America/Bogota')

    same_day = df_merge_firsts['created_at'].dt.date == df_merge_firsts['first_reply_created_at'].dt.date
    df_merge_firsts['tiempo_respuesta_minutos'] = np.where(
        same_day,
        (df_merge_firsts.apply(calcular_mismo_dia, axis=1) / 60).round(2),
        (df_merge_firsts.apply(calcular_dia_distinto, axis=1) / 60).round(2)
    )

    promedio_agente = df_merge_firsts.groupby('sender_id')['tiempo_respuesta_minutos'].mean().reset_index(name='promedio_min')


    promedio_agente["sender_id"] = promedio_agente["sender_id"].map(agentes).fillna(promedio_agente["sender_id"])
    # Agregamos formato legible y ordenamos de menor a mayor (mejor tiempo primero)
    promedio_agente_sorted = promedio_agente.sort_values('promedio_min', ascending=True).copy()
    promedio_agente_sorted['legible'] = promedio_agente_sorted['promedio_min'].apply(minutos_a_hhmm)

    return {
        "metadatos": {
            "total_conversaciones_analizadas": len(df_merge_firsts),
            "agentes_excluidos_sistema": ids_agentes_ignorar,
            "nota": "Usa el mismo criterio de horario laboral que promedio_primera_respuesta"
        },
        "datos": promedio_agente_sorted.to_dict(orient="records")
    }, promedio_agente_sorted
    

def graficar(promedio_agente_sorted: pd.DataFrame, output_path: str):
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
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("✅ barras_primera_respuesta_agente.png guardado")
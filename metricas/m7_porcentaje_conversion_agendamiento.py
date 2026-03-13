import pandas as pd
import matplotlib.pyplot as plt

def calcular(df: pd.DataFrame):
    df_iniciadas_agendamiento = df[
        df['cached_label_list'].str.contains(
            r'(?:^|,)agendamiento(?:$|,)', regex=True, na=False
        )
    ]

    agendamiento_exitoso = df_iniciadas_agendamiento[df_iniciadas_agendamiento['cached_label_list'].str.contains('agendamiento_exitoso')]
    porcentaje_exito_sobre_iniciadas = (len(agendamiento_exitoso) / len(df_iniciadas_agendamiento)) * 100


    # Porcentaje de conversaciones no iniciadas en agendamiento que se agendaron
    df_no_iniciadas_agendamiento = df[
        ~df['cached_label_list'].str.contains(
            r'(?:^|,)agendamiento(?:$|,)', regex=True, na=False
        )
    ]

    no_iniciadas_agendamiento_agendadas = df_no_iniciadas_agendamiento[df_no_iniciadas_agendamiento['cached_label_list'].str.contains('agendamiento_exitoso', na=False)]
    porcentaje_exito_no_iniciadas = (len(no_iniciadas_agendamiento_agendadas) / len(df_no_iniciadas_agendamiento)) * 100


    #Porcentaje de conversaciones agendadas
    agendamiento_exitoso = df[df['cached_label_list'].str.contains('agendamiento_exitoso', na=False)]

    cant_agendadas = len(agendamiento_exitoso)

    porcentaje_total_agendadas = (cant_agendadas / len(df))*100
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

    return {
        "metadatos": {
            "total_conversaciones":              len(df),
            "total_iniciadas_agendamiento":      len(df_iniciadas_agendamiento),
            "total_no_iniciadas_agendamiento":   len(df_no_iniciadas_agendamiento),
            "total_agendadas_exitosas":          cant_agendadas,
        },
        "datos": {
            "tabla": df_metricas_agendamiento.to_dict(orient="records"),
            "pie_chart": [
                {"label": "Agendadas exitosas", "cantidad": cant_agendadas,              "porcentaje": round(porcentaje_total_agendadas, 2)},
                {"label": "No agendadas",        "cantidad": len(df) - cant_agendadas,   "porcentaje": round(100 - porcentaje_total_agendadas, 2)}
            ]
        }
    }, cant_agendadas, len(df)

def graficar(cant_agendadas: int, total: int, output_path: str):

    labels_pie = ["Agendadas exitosas", "No agendadas"]
    sizes_pie  = [cant_agendadas, total - cant_agendadas]
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
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("✅ torta_agendamientos.png guardado")
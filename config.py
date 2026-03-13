from sqlalchemy import create_engine

engine = create_engine("postgresql+psycopg2://intern_new:internpass_new@localhost:5434/intern_db_new")
engine2 = create_engine("postgresql+psycopg2://intern:internpass@localhost:5433/intern_db")

year_rp = 2026
month_rp = 1
start_day = 1
end_day = 30

agentes = {
    6: 'Andres echeverry',
    10: 'Viviana',
    12: 'Jenny',
    13: 'Edwar',
    15: 'Diana',
    16: 'Yoan'
}

mapa_dias = {
    0: "lunes",
    1: "martes",
    2: "miercoles",
    3: "jueves",
    4: "viernes",
    5: "sabado",
    6: "domingo"
}

ids_agentes_ignorar = [1, 11, 14, 9]


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

ppm = 40 
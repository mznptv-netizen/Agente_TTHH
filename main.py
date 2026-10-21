import datetime
import os
import sqlite3
from google import genai
import pywhatkit as kit

# 1. PEGA AQUÍ TU API KEY DE GOOGLE AI STUDIO
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AQ.Ab8RN6K5xK3Fe8hQa_U1XSDJYYBQat9QFshIqUGontjBHnqC3A")

# 2. PEGA AQUÍ EL NÚMERO DE WHATSAPP DESTINO (Ejemplo: "+573001234567")
NUMERO_WHATSAPP = "+573102249777"


def obtener_rutas():
  """Define y crea la carpeta propia de Valeria y las rutas de BD."""
  local_appdata = os.getenv("LOCALAPPDATA")

  # Ruta base de IPSICOL
  ruta_ipsicol = os.path.join(local_appdata, "IPSICOL", "TalentoHumano")

  # Carpeta dedicada exclusivamente a la memoria y archivos de Valeria
  carpeta_valeria = os.path.join(ruta_ipsicol, "AgenteValeria")

  if not os.path.exists(carpeta_valeria):
    os.makedirs(carpeta_valeria, exist_ok=True)

  # Ruta de la base de datos de empleados y la memoria de Valeria
  ruta_bd_empleados = os.path.join(ruta_ipsicol, "talento_humano.db")
  ruta_bd_memoria = os.path.join(carpeta_valeria, "memoria_valeria.db")

  return ruta_bd_empleados, ruta_bd_memoria


def inicializar_memoria():
  """Crea la base de datos y la tabla de memoria en la carpeta de Valeria."""
  _, ruta_bd_memoria = obtener_rutas()
  try:
    conexion = sqlite3.connect(ruta_bd_memoria)
    cursor = conexion.cursor()
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                emisor TEXT,
                mensaje TEXT
            )
        """)
    conexion.commit()
    conexion.close()
  except Exception as e:
    print(f"Error al inicializar la memoria de Valeria: {e}")


def guardar_en_memoria(emisor, mensaje):
  """Guarda los mensajes en la BD de memoria de Valeria."""
  _, ruta_bd_memoria = obtener_rutas()
  try:
    conexion = sqlite3.connect(ruta_bd_memoria)
    cursor = conexion.cursor()
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO historial_chat (fecha, emisor, mensaje) VALUES (?, ?, ?)",
        (fecha_actual, emisor, mensaje),
    )
    conexion.commit()
    conexion.close()
  except Exception as e:
    print(f"Error guardando memoria: {e}")


def obtener_historial_memoria(limite=10):
  """Recupera el contexto de conversaciones anteriores."""
  _, ruta_bd_memoria = obtener_rutas()
  if not os.path.exists(ruta_bd_memoria):
    return ""

  try:
    conexion = sqlite3.connect(ruta_bd_memoria)
    cursor = conexion.cursor()
    cursor.execute(
        "SELECT fecha, emisor, mensaje FROM historial_chat ORDER BY id DESC"
        " LIMIT ?",
        (limite,),
    )
    filas = cursor.fetchall()
    conexion.close()

    filas.reverse()

    texto_memoria = "--- CONTEXTO DE CHARLAS ANTERIORES ---\n"
    for fecha, emisor, mensaje in filas:
      texto_memoria += f"[{fecha}] {emisor}: {mensaje}\n"
    texto_memoria += "-------------------------------------\n"
    return texto_memoria
  except Exception as e:
    return f"Error al leer memoria: {e}"


def consultar_empleados_bd():
  """Lee la información de los empleados desde la BD original."""
  ruta_bd_empleados, _ = obtener_rutas()
  if not os.path.exists(ruta_bd_empleados):
    return (
        None,
        f"No se encontró el archivo 'talento_humano.db' en {ruta_bd_empleados}",
    )

  try:
    conexion = sqlite3.connect(ruta_bd_empleados)
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM empleados")
    filas = cursor.fetchall()

    cursor.execute("PRAGMA table_info(empleados)")
    columnas = [col[1] for col in cursor.fetchall()]
    conexion.close()
    return columnas, filas
  except Exception as e:
    return None, f"Error al leer empleados: {e}"


def consultar_a_valeria(pregunta_usuario):
  """Envía la pregunta a Gemini combinando empleados, memoria e identidad de Valeria."""
  columnas, datos = consultar_empleados_bd()
  memoria = obtener_historial_memoria(limite=10)

  texto_datos = f"Columnas: {columnas}\nRegistros:\n"
  if datos and isinstance(datos, list):
    for fila in datos:
      texto_datos += f"{fila}\n"

  prompt = f"""
    Eres Valeria, la Agente de Inteligencia Artificial del departamento de Talento Humano de IPSICOL.
    Tu labor es orientar, responder preguntas y alertar sobre la gestión del personal.

    INFORMACIÓN ACTUAL DE EMPLEADOS DE IPSICOL:
    {texto_datos}

    MEMORIA DE CONVERSACIONES PREVIAS CON EL USUARIO:
    {memoria}

    NUEVA CONSULTA DEL USUARIO: "{pregunta_usuario}"

    Responde de forma profesional, directa y formal.
    """

  guardar_en_memoria("Usuario", pregunta_usuario)

  client = genai.Client(api_key=GEMINI_API_KEY)
  respuesta = client.models.generate_content(
      model="gemini-2.5-flash", contents=prompt
  )

  guardar_en_memoria("Valeria", respuesta.text)
  return respuesta.text


def enviar_presentacion_whatsapp():
  """Genera el reporte inicial y envía la presentación oficial por WhatsApp."""
  print("🤖 Valeria está analizando la base de datos de IPSICOL...")
  reporte_inicial = consultar_a_valeria(
      "Por favor realiza un análisis rápido e identifica alertas sobre contratos"
      " o vencimientos próximos."
  )

  presentacion = (
      "👋 ¡Hola! Soy *Valeria*, tu Agente de Inteligencia Artificial para el"
      " área de *Talento Humano de IPSICOL*.\n\nEstoy aquí para ayudarte a"
      " optimizar la gestión del equipo. Mis funciones principales son:\n"
      "1. 🚨 *Monitorear alertas:* Te aviso automáticamente sobre vencimientos"
      " de contratos y prórrogas.\n"
      "2. 💬 *Resolver consultas con memoria:* Recuerdo nuestras charlas"
      " pasadas y puedo darte detalles de empleados, EPS, sedes y más.\n\nAquí"
      " tienes el primer reporte generado hoy:\n\n"
      f"{reporte_inicial}"
  )

  try:
    print("📲 Enviando presentación y reporte por WhatsApp...")
    kit.sendwhatmsg_instantly(
        phone_no=NUMERO_WHATSAPP,
        message=presentacion,
        wait_time=15,
        tab_close=True,
    )
    print("¡Mensaje enviado con éxito por WhatsApp!")
  except Exception as e:
    print(f"Error enviando mensaje a WhatsApp: {e}")


if __name__ == "__main__":
  inicializar_memoria()

  print("==================================================")
  print("   🤖 VALERIA - AGENTE TALENTO HUMANO (IPSICOL)  ")
  print("==================================================")

  # Enviar la presentación oficial por WhatsApp al iniciar
  enviar_presentacion_whatsapp()

  # Modo chat interactivo continuo con memoria
  print("\n--- CHAT ACTIVO CON VALERIA (Escribe 'salir' para finalizar) ---")
  while True:
    pregunta = input("\n🧑‍💼 Tú: ").strip()
    if pregunta.lower() in ["salir", "exit", "chao"]:
      print("\n🤖 Valeria: ¡Hasta luego! Todo quedó guardado en mi memoria.")
      break
    if not pregunta:
      continue

    respuesta = consultar_a_valeria(pregunta)
    print(f"\n🤖 Valeria (IPSICOL):\n{respuesta}")

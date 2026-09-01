import streamlit as st
import streamlit.components.v1 as components
import json
import os
import pickle
import io
import smtplib
import requests
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Configuración de página de Streamlit
st.set_page_config(
    page_title="Ficha Creativa: Mesa de Mezclas",
    page_icon="🎛️",
    layout="centered"
)

# ---- OCULTAR BARRAS SUPERIOR E INFERIOR (SISTEMA QUIRÚRGICO TROPICARNES) ----
hide_streamlit_style = """
    <style>
    /* Ocultar por completo la cabecera (Share, GitHub, 3 puntos) */
    [data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Ocultar pie de página y línea decorativa */
    footer {visibility: hidden; display: none !important;}
    div[data-testid="stDecoration"] {display: none !important;}
    #stConnectionStatus {display: none !important;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Vigilante permanente con MutationObserver para "Manage app" y badges de Streamlit
components.html(
    """
    <script>
    (function () {
        const SELECTORES = [
            'a[href*="streamlit.io"]',
            'a[href*="share.streamlit.io"]',
            '[class*="viewerBadge"]',
            '[class*="StatusWidget"]',
            '[data-testid="stStatusWidget"]',
            '[data-testid="stToolbar"]',
            'iframe[title="Manage app"]',
            'button[data-testid="manage-app-button"]'
        ];

        function ocultarEn(doc) {
            if (!doc) return;
            SELECTORES.forEach(function (sel) {
                doc.querySelectorAll(sel).forEach(function (el) {
                    el.style.setProperty("display", "none", "important");
                    el.style.setProperty("visibility", "hidden", "important");
                    el.style.setProperty("pointer-events", "none", "important");
                });
            });
        }

        function ejecutar() {
            try { ocultarEn(window.top.document); } catch (e) {}
            ocultarEn(document);
        }

        ejecutar();

        try {
            const observer = new MutationObserver(ejecutar);
            observer.observe(window.top.document.body, { childList: true, subtree: true });
        } catch (e) {}

        setInterval(ejecutar, 1000);
    })();
    </script>
    """,
    height=0,
)

# ID de la carpeta raíz receptora en Google Drive (Entregas_Taller)
PARENT_FOLDER_ID = '1sPd8kqGLcEDXVFPzHxAkKrdcLzDhhkPg'

# SYSTEM PROMPT DEL AGENTE TRADUCTOR VÉNTUM (ELEMENTO A)
SYSTEM_PROMPT_TRADUCTOR = """
Eres el Agente Estratega y Traductor de Arquitectura Web de Véntum. Tu función es recibir información heterogénea de clientes o diseñadores y traducirla a la Ficha Técnica JSON Maestra de Véntum para la fábrica de código.

REGLAS DE INGERENCIA Y PROCESAMIENTO:
1. INGESTA TRIMODAL:
   - Modo 1 (Texto/Brief): Analiza el nicho comercial, selecciona una psicología de color óptima y redacta titulares y llamados a la acción de alto impacto.
   - Modo 2 (Imagen/Boceto/PDF): Extrae la paleta cromática real en Hexadecimal (#HEX), detecta los bloques visuales y mapea la distribución exacta.
   - Modo 3 (Figma Auto Layout): Lee padding, gap, flexbox, colores de marca y tipografía, trasládalos sin alteración.

2. ANTI-CEGUERA DE PLANTILLA (ARQUETIPOS OBLIGATORIOS):
   Debes asignar OBLIGATORIAMENTE uno de los siguientes 5 arquetipos de layout:
   - 'Bento Grid': Mosaico asimétrico de tarjetas interactivas (Tech, agencias, portafolios).
   - 'Split Screen': Pantalla dividida 50/50 (Servicios profesionales, consultorías).
   - 'App Interface': Marcos reducidos, estética móvil con botones de acción rápida (Comida, menús, catálogos express).
   - 'Editorial Minimal': Tipografía Serif, espacios amplios en blanco (Arquitectura, lujo, salud).
   - 'Landing Directa': Estructura vertical clásica de alta conversión con formulario directo.

3. RESTRICCIÓN DE SALIDA (CRÍTICO):
   Tu respuesta debe contener ÚNICA Y EXCLUSIVAMENTE el objeto JSON válido y formateado, sin introducciones ni textos explicativos.

ESQUEMA JSON DE SALIDA OBLIGATORIO:
{
    "cliente": "Nombre o Nicho",
    "concepto": "Propuesta de valor principal",
    "tono": ["Atributo1", "Atributo2"],
    "arquetipo_layout": "NombreDelArquetipo",
    "ritmo_espacial": "Descripción geométrica del espacio visual",
    "hero": {
        "estilo": "Descripción del layout del hero",
        "titular_principal": "Texto titular",
        "subtitulo": "Descripción en 2 líneas",
        "badge_destacado": "Texto de garantía o estatus",
        "llamados_accion": ["CTA Principal", "CTA Secundario"]
    },
    "modulos": ["Modulo 1", "Modulo 2", "Modulo 3", "Modulo 4"],
    "elementos_digitales_existentes": [
        {
            "nombre_sistema": "Nombre del módulo o app preexistente",
            "url_destino": "https://link-del-sistema.com",
            "tipo_integracion": "boton_cta_destacado | widget_flotante | iframe_modal",
            "ubicacion_en_web": ["hero", "menu_navegacion", "boton_flotante"],
            "texto_accion": "Texto del botón de llamado a la acción",
            "icono_sugerido": "fa-shopping-cart | fa-calculator | fa-whatsapp"
        }
    ],
    "conversion": {
        "boton_flotante": "Acción del botón flotante",
        "formulario": "Campos de captura requeridos",
        "canales_directos": ["Canal 1", "Canal 2"]
    },
    "identidad_visual": {
        "color_dominante": "#HEX",
        "color_secundario": "#HEX",
        "color_acento": "#HEX",
        "tipografia": "Estilo tipográfico sugerido",
        "iconografia": "FontAwesome CDN"
    },
    "canales_digitales": {
        "instagram": "@usuario",
        "tiktok": "@usuario",
        "whatsapp": "+58XXXXXXXXXX"
    }
}
"""

def obtener_servicio_drive():
    """Obtiene el servicio de Drive desde token.json local o st.secrets."""
    creds = None
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'rb') as token:
                creds = pickle.load(token)
        except Exception as e:
            st.error(f"Error al leer el archivo 'token.json' local: {e}")
            return None
    elif "GOOGLE_TOKEN_PICKLE" in st.secrets:
        try:
            token_bytes = base64.b64decode(st.secrets["GOOGLE_TOKEN_PICKLE"])
            creds = pickle.loads(token_bytes)
        except Exception as e:
            st.error(f"Error al decodificar las credenciales desde Secrets: {e}")
            return None
    else:
        st.error("No se encontraron credenciales de Google Drive (token.json no existe y GOOGLE_TOKEN_PICKLE no está en Secrets).")
        return None

    try:
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        st.error(f"Error al conectar con la API de Google Drive: {e}")
        return None

def crear_carpeta_proyecto(service, nombre_carpeta, parent_id):
    """Crea una subcarpeta para el proyecto dentro de Entregas_Taller."""
    try:
        file_metadata = {
            'name': nombre_carpeta,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    except Exception as e:
        st.error(f"Error al crear la carpeta del proyecto en Google Drive: {e}")
        return None

def subir_a_google_drive(service, uploaded_file, target_folder_id):
    """Sube un archivo a la carpeta del proyecto en Google Drive."""
    try:
        file_metadata = {
            'name': uploaded_file.name,
            'parents': [target_folder_id]
        }
        media = MediaIoBaseUpload(
            io.BytesIO(uploaded_file.getvalue()),
            mimetype=getattr(uploaded_file, 'type', 'application/octet-stream') or 'application/octet-stream',
            resumable=True
        )
        archivo = service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
        return archivo
    except Exception as e:
        st.error(f"Error al subir '{uploaded_file.name}' a Google Drive: {e}")
        return None

def ejecutar_traductor_gemini(ficha_datos):
    """Llama a la API de Gemini para generar la Ficha JSON Maestra de VÉNTUM."""
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.warning("⚠️ No se encontró GEMINI_API_KEY en st.secrets. Se omitió la traducción automática.")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt_usuario = (
        "Analiza la siguiente Ficha Creativa enviada desde la Mesa de Mezclas y genera "
        "la Ficha JSON Maestra de VÉNTUM siguiendo estrictamente el esquema del sistema:\n\n"
        f"{json.dumps(ficha_datos, ensure_ascii=False, indent=2)}"
    )

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt_usuario}]}
        ],
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT_TRADUCTOR}]
        },
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        }
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            res_data = response.json()
            raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(raw_text)
        else:
            st.error(f"Error API Gemini ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        st.warning(f"No se pudo completar la traducción con Gemini: {e}")
        return None

def enviar_notificacion_email(cliente, nombre_carpeta, modalidad, cant_archivos, tiene_json_maestro):
    """Envía un correo al taller cuando entra una nueva ficha."""
    smtp_server = st.secrets.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(st.secrets.get("SMTP_PORT", 587))
    remitente = st.secrets.get("EMAIL_REMITENTE", "")
    password = st.secrets.get("EMAIL_PASSWORD", "")
    destinatario = st.secrets.get("EMAIL_DESTINATARIO", remitente)

    if not remitente or not password:
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = remitente
        msg['To'] = destinatario
        msg['Subject'] = f"🔔 Nueva Ficha Creativa Registrada: {cliente}"

        cuerpo = f"""
        ¡Atención Taller VÉNTUM!

        Se ha registrado y procesado una nueva Ficha Creativa.

        📋 Resumen de la Entrega:
        --------------------------------------------------
        • Cliente / Proyecto: {cliente}
        • Carpeta en Drive: {nombre_carpeta}
        • Modalidad: {modalidad}
        • Insumos adjuntos: {cant_archivos} archivo(s)
        • Ficha JSON Maestra VÉNTUM: {"✅ Generada y lista" if tiene_json_maestro else "⚠️ Manual"}
        • Fecha/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        --------------------------------------------------

        Toda la información ha sido guardada en la carpeta correspondiente de Google Drive.
        """
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(remitente, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.warning(f"No se pudo enviar la alerta por correo electrónico: {e}")
        return False

def enviar_notificacion_whatsapp(cliente, nombre_carpeta, modalidad, cant_archivos, json_maestro):
    """Envía un mensaje de WhatsApp directo con el JSON Maestro formateado vía Green API."""
    id_instance = st.secrets.get("GREEN_ID_INSTANCE", "")
    api_token = st.secrets.get("GREEN_API_TOKEN", "")
    numero = st.secrets.get("WHATSAPP_DESTINO", "").replace("+", "").strip()

    if not id_instance or not api_token or not numero:
        return False

    url = f"https://api.green-api.com/waInstance{id_instance}/sendMessage/{api_token}"
    chat_id = f"{numero}@c.us"
    
    str_json = json.dumps(json_maestro, ensure_ascii=False, indent=2) if json_maestro else "No generado"
    
    mensaje = (
        f"🔔 *¡NUEVA FICHA CREATIVA EN VÉNTUM!*\n\n"
        f"👤 *Cliente / Proyecto:* {cliente}\n"
        f"📁 *Carpeta Drive:* `{nombre_carpeta}`\n"
        f"⚙️ *Modalidad:* {modalidad}\n"
        f"📎 *Insumos adjuntos:* {cant_archivos} archivo(s)\n"
        f"📅 *Fecha:* {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        f"📋 *FICHA MAESTRA JSON (Para AI Studio):*\n```json\n{str_json}\n```"
    )

    payload = {
        "chatId": chat_id,
        "message": mensaje
    }
    headers = {'Content-Type': 'application/json'}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        return res.status_code == 200
    except Exception as e:
        st.warning(f"No se pudo enviar la alerta por WhatsApp: {e}")
        return False

# --- ENCABEZADO PRINCIPAL CENTRADO ---
st.markdown("<h1 style='text-align: center;'>Ficha Creativa: Mesa de Mezclas</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>Estudio de Diseño Web - VÉNTUM | Lic. Daniel Pineda</p>", unsafe_allow_html=True)
st.write("")

# --- BLOQUE 1 ---
with st.container():
    st.subheader("Bloque 1: Vibe y Dirección Creativa")
    cliente = st.text_input("Nombre del Proyecto / Cliente*", placeholder="Ej: Tropicarnes / Juan Pérez")
    concepto = st.text_area("Concepto en una frase", placeholder="La historia o idea central del cliente...")
    
    col1, col2 = st.columns(2)
    with col1:
        tono = st.multiselect(
            "Tono deseado",
            ["Elegante & Sofisticado", "Moderno & Minimalista", "Cálido & Cercano", "Audaz & Disruptivo", "Profesional & Corporativo", "Otros"]
        )
    with col2:
        tono_otros = st.text_input("Si elegiste 'Otros' en Tono, descríbelo:", placeholder="Especifica el tono...")
        
    instrucciones_libres = st.text_area("Instrucciones Libres", placeholder="Cualquier requerimiento estético, detalle o referencia que quieras ver plasmado...")

# --- BLOQUE 2 ---
with st.container():
    st.subheader("Bloque 2: Arquitectura Modular (Elige y Combina)")
    
    hero = st.radio(
        "Encabezado / Hero Section",
        [
            "Impacto Visual (Imagen/Video a pantalla completa + Acción)",
            "Tipográfico / Minimalista (Frase potente + Diseño limpio)",
            "Doble Columna (Texto + Tarjeta o Producto destacado)",
            "Formulario Directo (Captura de datos o cotización)",
            "Otros"
        ]
    )
    hero_otros = st.text_input("Si elegiste 'Otros' en Encabezado, descríbelo:", placeholder="Detalla el encabezado...")
    
    modulos = st.multiselect(
        "Módulos del Sitio (Selecciona los que necesites)",
        ["Servicios / Catálogo", "Sobre Nosotros / Historia", "Galería de Fotos / Portafolio", "Testimonios / Reseñas", "Preguntas Frecuentes (FAQ)", "Contacto & Mapa", "Otros"]
    )
    modulos_otros = st.text_input("Si elegiste 'Otros' en Módulos, descríbelos:", placeholder="Detalla los módulos...")
    
    conversion = st.multiselect(
        "Cierre y Conversión",
        ["Botón Flotante de WhatsApp", "Formulario de Contacto Directo", "Enlace a Redes Sociales", "Llamada a la Acción (CTA) Final", "Otros"]
    )
    conversion_otros = st.text_input("Si elegiste 'Otros' en Cierre y Conversión, descríbelo:", placeholder="Detalla los cierres...")

# --- BLOQUE 3 ---
with st.container():
    st.subheader("Bloque 3: Estilo Visual & Paleta")
    col3, col4 = st.columns(2)
    with col3:
        color_opcion = st.selectbox(
            "Colores",
            ["Subir guía o manual de marca", "Indicar colores clave u 'Otros'"]
        )
        colores_detalle = st.text_input("Si elegiste 'Indicar colores clave' u 'Otros', especifica:", placeholder="Ej: Azul Marino y Dorado")
    with col4:
        tipografia = st.selectbox(
            "Tipografía",
            ["Moderna Sans-Serif", "Clásica Serif", "Manuscrita / Creativa", "Otros"]
        )
        tipografia_otros = st.text_input("Si elegiste 'Otros' en Tipografía, descríbelo:", placeholder="Nombre de fuente o estilo...")

# --- BLOQUE 4 ---
with st.container():
    st.subheader("Bloque 4: Zona de Descarga (Insumos para Drive)")
    archivos_cargados = st.file_uploader(
        "Arrastra o selecciona aquí los insumos desde tu PC",
        accept_multiple_files=True,
        help="Puedes subir imágenes, documentos PDF, textos o guías de marca."
    )
    st.caption("Todos los archivos cargados se guardarán automáticamente en una carpeta dedicada dentro de Entregas_Taller en Google Drive.")

# --- BLOQUE 5 ---
with st.container():
    st.subheader("Bloque 5: Modalidad de Trabajo & Compromiso")
    modalidad = st.radio(
        "Modalidad de Trabajo",
        [
            "Modo Taller: El taller ensambla la web al 100% y te entrega el borrador funcional listo para tu visto bueno.",
            "Modo Co-creación: El taller arma la estructura base y los contenidos para que tú hagas los ajustes finos de diseño sobre la marcha."
        ]
    )
    
    enviar = st.button("Enviar a la Línea de Ensamblaje del Taller", type="primary", use_container_width=True)

# --- PROCESAMIENTO AL HACER CLIC EN ENVIAR ---
if enviar:
    if not cliente:
        st.warning("Por favor ingresa el Nombre del Proyecto / Cliente antes de enviar.")
    else:
        service = obtener_servicio_drive()
        
        if service:
            # 1. Crear carpeta individualizada para el proyecto
            with st.spinner("Creando carpeta dedicada para el proyecto en Google Drive..."):
                timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
                nombre_carpeta_proyecto = f"Proyecto - {cliente} ({timestamp_str})"
                project_folder_id = crear_carpeta_proyecto(service, nombre_carpeta_proyecto, PARENT_FOLDER_ID)

            if project_folder_id:
                archivos_subidos_drive = []
                
                # 2. Subir insumos a Google Drive
                if archivos_cargados:
                    with st.spinner("Subiendo insumos a la carpeta del proyecto..."):
                        exitosos = 0
                        for archivo in archivos_cargados:
                            res = subir_a_google_drive(service, archivo, project_folder_id)
                            if res:
                                exitosos += 1
                                archivos_subidos_drive.append({
                                    "nombre": archivo.name,
                                    "id": res.get("id"),
                                    "link": res.get("webViewLink")
                                })
                        if exitosos > 0:
                            st.success(f"{exitosos} archivo(s) de insumos subido(s) correctamente.")

                # 3. Compilar datos de la ficha recibida
                ficha_datos = {
                    "fecha_ingreso": str(datetime.now()),
                    "cliente": cliente,
                    "concepto": concepto,
                    "tono": tono,
                    "tono_otros": tono_otros,
                    "instrucciones_libres": instrucciones_libres,
                    "hero": hero,
                    "hero_otros": hero_otros,
                    "modulos": modulos,
                    "modulos_otros": modulos_otros,
                    "conversion": conversion,
                    "conversion_otros": conversion_otros,
                    "color_opcion": color_opcion,
                    "colores_detalle": colores_detalle,
                    "tipografia": tipografia,
                    "tipografia_otros": tipografia_otros,
                    "archivos_drive": archivos_subidos_drive,
                    "modalidad": modalidad
                }

                class BytesFile:
                    def __init__(self, content, name):
                        self.content = content
                        self.name = name
                        self.type = 'application/json'
                    def getvalue(self):
                        return self.content

                # 4. Guardar archivo JSON raw original
                nombre_json_raw = f"Ficha_Raw_{cliente.replace(' ', '_')}.json"
                json_raw_bytes = json.dumps(ficha_datos, indent=4, ensure_ascii=False).encode('utf-8')
                subir_a_google_drive(service, BytesFile(json_raw_bytes, nombre_json_raw), project_folder_id)

                # 5. Ejecutar Traductor Gemini (Elemento A) -> Ficha JSON Maestra VÉNTUM
                json_maestro_ventum = None
                with st.spinner("⚡ Procesando Traductor Universal VÉNTUM con Gemini IA..."):
                    json_maestro_ventum = ejecutar_traductor_gemini(ficha_datos)

                if json_maestro_ventum:
                    nombre_json_maestro = f"Ficha_Maestra_VENTUM_{cliente.replace(' ', '_')}.json"
                    json_maestro_bytes = json.dumps(json_maestro_ventum, indent=4, ensure_ascii=False).encode('utf-8')
                    subir_a_google_drive(service, BytesFile(json_maestro_bytes, nombre_json_maestro), project_folder_id)

                # 6. Enviar notificaciones (Email + WhatsApp)
                with st.spinner("Enviando alertas de notificación al equipo VÉNTUM..."):
                    email_ok = enviar_notificacion_email(
                        cliente=cliente,
                        nombre_carpeta=nombre_carpeta_proyecto,
                        modalidad=modalidad,
                        cant_archivos=len(archivos_subidos_drive),
                        tiene_json_maestro=json_maestro_ventum is not None
                    )
                    wa_ok = enviar_notificacion_whatsapp(
                        cliente=cliente,
                        nombre_carpeta=nombre_carpeta_proyecto,
                        modalidad=modalidad,
                        cant_archivos=len(archivos_subidos_drive),
                        json_maestro=json_maestro_ventum
                    )

                # 7. Confirmación final e interactiva en UI
                st.success(f"Ficha registrada y traducida con éxito para {cliente}. Información organizada en '{nombre_carpeta_proyecto}'.")
                
                if json_maestro_ventum:
                    st.subheader("📋 Ficha JSON Maestra VÉNTUM (Lista para AI Studio)")
                    st.code(json.dumps(json_maestro_ventum, ensure_ascii=False, indent=2), language="json")

                with st.expander("Resumen de la solicitud enviada", expanded=True):
                    st.markdown(f"**Cliente / Proyecto:** {cliente}")
                    st.markdown(f"**Carpeta en Drive:** {nombre_carpeta_proyecto}")
                    st.markdown(f"**Modalidad:** {modalidad}")
                    st.markdown(f"**Archivos adjuntos:** {len(archivos_subidos_drive)} archivo(s)")
                    
                    alertas = []
                    if email_ok: alertas.append("Correo")
                    if wa_ok: alertas.append("WhatsApp")
                    
                    if alertas:
                        st.info(f"Notificación enviada vía: {', '.join(alertas)}.")
                    else:
                        st.info("La carpeta ha sido creada y organizada en la unidad de Google Drive del Taller.")
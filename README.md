# MANTENIA – Gemini + Google Search + documentos PDF

Esta versión sustituye OpenAI por Google Gemini API. Conserva Streamlit y GitHub, incorpora Google Search Grounding y permite cargar documentos PDF, DOCX, TXT, MD y CSV para recuperación documental (RAG) sencilla.

## 1. Crear una clave de Gemini
1. Entra en https://aistudio.google.com/app/apikey
2. Inicia sesión con tu cuenta Google.
3. Crea una API key.
4. No publiques la clave en GitHub ni la pegues en `app.py`.

El acceso gratuito está sujeto a disponibilidad, modelos admitidos, cuotas y límites que Google puede modificar. Consulta https://ai.google.dev/gemini-api/docs/pricing y https://ai.google.dev/gemini-api/docs/rate-limits. La búsqueda con Google Search también tiene límites propios según modelo y nivel de uso; no presupongas que es ilimitada ni siempre gratuita.

## 2. Archivos del proyecto
- `app.py`: aplicación Streamlit con Gemini, búsqueda web y carga documental.
- `requirements.txt`: dependencias.
- `secrets.toml.example`: plantilla de configuración.
- `README.md`: estas instrucciones.

## 3. Configurar Streamlit Cloud
1. Abre tu repositorio GitHub `MANTENIA-Chatbot`.
2. Reemplaza el `app.py` anterior por este `app.py`.
3. Reemplaza `requirements.txt`.
4. Sube también `README.md` y `secrets.toml.example` si lo deseas.
5. En Streamlit Community Cloud, abre la aplicación → Manage app → Settings → Secrets.
6. Pega el siguiente contenido, reemplazando el valor por tu clave real:

```toml
GEMINI_API_KEY = "TU_CLAVE_REAL_DE_GEMINI"
GEMINI_MODEL = "gemini-2.5-flash-lite"
```

7. Guarda los cambios. Streamlit reiniciará la aplicación.

No agregues `OPENAI_API_KEY` ni `MANTENIA_VECTOR_STORE_ID`: esta versión ya no los utiliza.

## 4. Cargar manuales y procedimientos
1. Abre MANTENIA.
2. En la barra lateral, en «Base documental propia», pulsa Browse files / Upload.
3. Selecciona uno o varios PDF, DOCX, TXT, MD o CSV.
4. Pulsa «Procesar documentos».
5. Realiza una pregunta relacionada con el contenido.

**Importante sobre persistencia:** esta versión procesa los documentos en memoria de la sesión de Streamlit. Si la aplicación se reinicia o la sesión se pierde, tendrás que volver a cargar y procesar los documentos. Para un despliegue permanente, conviene añadir almacenamiento persistente autorizado (por ejemplo, almacenamiento de objetos o una base vectorial).

## 5. Ejecutar localmente
Requiere Python 3.10 o superior.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Crea `.streamlit/secrets.toml` con:

```toml
GEMINI_API_KEY = "TU_CLAVE_REAL_DE_GEMINI"
GEMINI_MODEL = "gemini-2.5-flash-lite"
```

Luego ejecuta:

```bash
streamlit run app.py
```

## 6. Qué cambió técnicamente
- `openai` se eliminó.
- Se utiliza `google-genai`.
- Gemini se invoca mediante `client.models.generate_content`.
- Google Search se activa con `types.Tool(google_search=types.GoogleSearch())`.
- Los PDF se extraen página por página con `pypdf`.
- Los DOCX se extraen con `python-docx`.
- Se recuperan fragmentos por coincidencia de términos y se incluyen en el contexto de Gemini.

## 7. Límites y seguridad
- El nivel gratuito de Gemini tiene límites de solicitudes, tokens y disponibilidad de modelos. Si se supera una cuota, la API puede devolver errores de límite (por ejemplo, 429).
- La disponibilidad gratuita de Google Search Grounding depende del modelo y del nivel de uso. Consulta siempre la página oficial de precios antes de publicar para usuarios externos.
- En el nivel gratuito, Google indica que el contenido puede utilizarse para mejorar sus productos. No cargues manuales confidenciales, información de clientes, datos personales, reportes internos o información operacional restringida sin autorización y revisión de las condiciones aplicables.
- La búsqueda web no convierte cualquier página en una fuente confiable. Prioriza fabricantes OEM, organismos oficiales, normas y publicaciones técnicas.
- Los documentos cargados se guardan en memoria de la sesión, no en una base documental persistente.
- MANTENIA es una herramienta de apoyo informativo; no sustituye manuales OEM, IPERC, permisos de trabajo ni la evaluación de personal competente.

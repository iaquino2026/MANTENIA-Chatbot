import os
import csv
import io
import tempfile
from pathlib import Path

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="MANTENIA | IA para mantenimiento", page_icon="🛠️", layout="wide")

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
MAX_UPLOAD_MB = 25
SUPPORTED = ["pdf", "docx", "xlsx", "csv", "txt", "md"]

def get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default

API_KEY = get_secret("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
CONFIGURED_STORE = get_secret("MANTENIA_VECTOR_STORE_ID") or os.getenv("MANTENIA_VECTOR_STORE_ID")

SYSTEM_PROMPT = """
Eres MANTENIA, asistente virtual especializado en gestión del mantenimiento de equipos
mineros e industriales. Responde en español, con lenguaje técnico claro y estructurado.

Prioriza los documentos recuperados de la base de conocimiento del usuario y distingue
claramente entre: (a) información encontrada en documentos, (b) conocimiento técnico
general y (c) inferencias. Cuando uses un documento, menciona su nombre y, si el sistema
proporciona la referencia, la página, hoja o sección. Si no encuentras evidencia suficiente,
dilo expresamente y no inventes datos, límites, intervalos, especificaciones OEM ni causas.

No asumas que una coincidencia temporal demuestra causalidad. En análisis de fallas,
diferencia hechos, hipótesis y causas confirmadas. Para cálculos, presenta fórmula, variables,
unidades y supuestos; no inventes datos faltantes.

Para frenos, dirección, izaje, alta tensión, combustibles, presión, riesgo de incendio o
cualquier intervención crítica, no des instrucciones operativas paso a paso. Recomienda
aplicar procedimientos del sitio, aislar/controlar energías cuando corresponda y derivar a
personal competente y documentación OEM aprobada.

No solicites ni reproduzcas placas, números de serie, nombres personales, credenciales,
datos contractuales, información de clientes o datos operacionales confidenciales.
Recomienda anonimizar archivos antes de cargarlos. Las respuestas no son diagnósticos
confirmados ni sustituyen la revisión de un especialista.
"""

KNOWLEDGE_PATH = Path(__file__).parent / "knowledge_base.md"
KNOWLEDGE = KNOWLEDGE_PATH.read_text(encoding="utf-8") if KNOWLEDGE_PATH.exists() else ""

def spreadsheet_to_markdown(uploaded_file):
    """Convierte Excel/CSV en texto tabular para indexación semántica."""
    name = uploaded_file.name
    suffix = Path(name).suffix.lower()
    chunks = [f"# Archivo de datos: {name}\n"]
    if suffix == ".csv":
        raw = uploaded_file.getvalue()
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            content = raw.decode("latin-1")
        rows = list(csv.reader(io.StringIO(content)))
        for idx, row in enumerate(rows[:1001], start=1):
            chunks.append(f"Fila {idx}: " + " | ".join(str(x) for x in row))
        if len(rows) > 1001:
            chunks.append(f"[Se omitieron {len(rows)-1001} filas por límite de procesamiento.]")
        return "\n".join(chunks)

    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(uploaded_file.getvalue()), data_only=True, read_only=True)
    for ws in wb.worksheets:
        chunks.append(f"\n## Hoja: {ws.title} ({ws.max_row} filas x {ws.max_column} columnas)\n")
        for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if r_idx > 1001:
                chunks.append("[Se omitieron filas adicionales por límite de procesamiento.]")
                break
            values = ["" if v is None else str(v) for v in row]
            if any(values):
                chunks.append(f"Fila {r_idx}: " + " | ".join(values))
    wb.close()
    return "\n".join(chunks)

def add_uploaded_file(client, vector_store_id, uploaded_file):
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md", ".xlsx", ".csv"}:
        raise ValueError("Formato no admitido. Usa PDF, DOCX, XLSX, CSV, TXT o MD.")

    if suffix in {".xlsx", ".csv"}:
        content = spreadsheet_to_markdown(uploaded_file)
        temp_suffix = ".md"
        temp_name = Path(uploaded_file.name).stem + "_convertido.md"
        payload = content.encode("utf-8")
    else:
        temp_suffix = suffix
        temp_name = uploaded_file.name
        payload = uploaded_file.getvalue()

    with tempfile.NamedTemporaryFile(suffix=temp_suffix, delete=False) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as fh:
            result = client.vector_stores.files.upload_and_poll(
                vector_store_id=vector_store_id,
                file=fh
            )
        return temp_name, result
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

st.title("🛠️ MANTENIA")
st.subheader("Asistente generativo para la gestión del mantenimiento de equipos mineros")
st.caption("OpenAI Responses API · Búsqueda documental (RAG) · Streamlit")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = CONFIGURED_STORE

with st.sidebar:
    st.header("Base documental")
    st.markdown("Carga manuales, procedimientos e historiales anonimizados para que MANTENIA pueda buscar información en ellos.")
    if st.session_state.vector_store_id:
        st.success("Base documental conectada")
        st.code(st.session_state.vector_store_id, language="text")
    else:
        st.info("Aún no existe una base documental.")
    if st.button("Crear base documental", disabled=not API_KEY, use_container_width=True):
        try:
            client = OpenAI(api_key=API_KEY)
            vs = client.vector_stores.create(name="MANTENIA - Base de conocimiento")
            st.session_state.vector_store_id = vs.id
            st.success("Base creada. Guarda el identificador como MANTENIA_VECTOR_STORE_ID en los secretos para conservarlo entre sesiones.")
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo crear la base: {str(exc)[:300]}")

    uploaded_files = st.file_uploader(
        "Selecciona documentos",
        type=SUPPORTED,
        accept_multiple_files=True,
        help="Formatos admitidos: PDF, DOCX, XLSX, CSV, TXT y MD. Máximo recomendado: 25 MB por archivo."
    )
    if st.button("Agregar documentos a la base", disabled=not (API_KEY and st.session_state.vector_store_id and uploaded_files), use_container_width=True):
        client = OpenAI(api_key=API_KEY)
        for uf in uploaded_files or []:
            if uf.size > MAX_UPLOAD_MB * 1024 * 1024:
                st.warning(f"{uf.name}: supera {MAX_UPLOAD_MB} MB y se omitió.")
                continue
            try:
                filename, result = add_uploaded_file(client, st.session_state.vector_store_id, uf)
                st.success(f"{filename}: indexación {getattr(result, 'status', 'enviada')}.")
            except Exception as exc:
                st.error(f"{uf.name}: no se pudo procesar. {str(exc)[:300]}")

    st.divider()
    st.header("Temas disponibles")
    st.markdown("""
    - Mantenimiento preventivo, correctivo y predictivo
    - Planificación, programación y órdenes de trabajo
    - MTBF, MTTR, disponibilidad y backlog
    - Confiabilidad, criticidad y análisis de causa raíz
    - Lubricación y gestión de activos
    - ISO 55001 e ISO 14224
    """)
    st.caption("No cargues información confidencial ni datos personales.")
    if st.button("Limpiar conversación", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

if not API_KEY:
    st.warning("Configura OPENAI_API_KEY en los secretos de Streamlit o como variable de entorno para activar la IA.")
if not st.session_state.vector_store_id:
    st.info("Para habilitar preguntas sobre tus archivos, crea primero una base documental en el panel lateral. También puedes conversar sobre el conocimiento general incluido.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if not st.session_state.messages:
    st.markdown("#### Consultas de ejemplo")
    samples = [
        "¿Cómo se calcula el MTBF y qué datos necesito?",
        "Compara las fallas registradas en el Excel que cargué.",
        "Resume los puntos críticos del procedimiento de mantenimiento.",
        "¿Qué acciones recomienda el historial para reducir el backlog?"
    ]
    cols = st.columns(2)
    for i, q in enumerate(samples):
        if cols[i % 2].button(q, key=f"sample_{i}", use_container_width=True):
            st.session_state.pending_prompt = q
            st.rerun()

prompt = st.chat_input("Escribe tu consulta sobre mantenimiento...")
if not prompt and st.session_state.get("pending_prompt"):
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if API_KEY:
        try:
            client = OpenAI(api_key=API_KEY)
            recent = st.session_state.messages[-12:]
            transcript = "\n\n".join(
                ("USUARIO: " if m["role"] == "user" else "MANTENIA: ") + m["content"]
                for m in recent
            )
            tools = []
            if st.session_state.vector_store_id:
                tools = [{
                    "type": "file_search",
                    "vector_store_ids": [st.session_state.vector_store_id],
                    "max_num_results": 8
                }]
            input_text = (
                "BASE DE CONOCIMIENTO GENERAL:\n" + KNOWLEDGE[:12000] +
                "\n\nHISTORIAL RECIENTE:\n" + transcript +
                "\n\nResponde a la última consulta del usuario. Si hay base documental conectada, "
                "utiliza file_search para recuperar evidencia antes de responder."
            )
            with st.chat_message("assistant"):
                with st.spinner("MANTENIA está consultando el conocimiento técnico..."):
                    response = client.responses.create(
                        model=MODEL,
                        instructions=SYSTEM_PROMPT,
                        input=input_text,
                        tools=tools
                    )
                    answer = response.output_text or "No se obtuvo texto de respuesta. Reformula la consulta."
                    st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except Exception as exc:
            answer = "No se pudo completar la consulta. Verifica la clave API, el identificador de la base documental y la conexión. Detalle: " + str(exc)[:400]
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.error(answer)
    else:
        answer = "Configura OPENAI_API_KEY para activar las respuestas generativas."
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.warning(answer)

st.divider()
st.caption("MANTENIA es una herramienta de apoyo informativo. No sustituye manuales OEM, procedimientos internos, IPERC, permisos de trabajo ni la evaluación de personal competente.")

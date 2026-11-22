import os
import re
from io import BytesIO

import streamlit as st
from google import genai
from google.genai import types
from pypdf import PdfReader
from docx import Document

st.set_page_config(
    page_title="MANTENIA | Asistente de mantenimiento",
    page_icon="🛠️",
    layout="wide",
)

def setting(name, default=""):
    try:
        value = st.secrets.get(name, None)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)

GEMINI_API_KEY = setting("GEMINI_API_KEY")
MODEL = setting("GEMINI_MODEL", "gemini-3.5-flash-lite")

SYSTEM_INSTRUCTIONS = """
Eres MANTENIA, asistente técnico de apoyo a la gestión del mantenimiento de equipos mineros.
Responde siempre en español, con lenguaje profesional, claro y estructurado.
Utiliza los extractos documentales proporcionados cuando sean pertinentes. Distingue lo que
procede de los documentos cargados de lo que procede de la búsqueda web. No inventes
normas, referencias, especificaciones, valores, intervalos ni procedimientos. Si los documentos
no contienen la respuesta, dilo. Para información actualizada, utiliza Google Search cuando
esté habilitado y cita las fuentes disponibles. Separa hechos, hipótesis y recomendaciones.
Para fallas, diagnóstico, reparación, lubricantes, ajustes o seguridad, no inventes parámetros
específicos de un modelo. Solicita marca, modelo, serie, sistema y condiciones de operación
cuando falten. Verifica siempre los manuales OEM y procedimientos aprobados. Ante riesgo,
indica detener la actividad y aplicar el procedimiento de control de energías y seguridad de
la operación bajo responsabilidad de personal competente. No sustituyas IPERC, permisos
de trabajo ni evaluación técnica. Para cálculos, muestra fórmula, unidades, datos requeridos
y supuestos.
"""

STOPWORDS = {
    "que","como","para","por","con","una","uno","unos","unas","del","las","los","una",
    "entre","sobre","desde","cuando","donde","cual","cuales","qué","cómo","porqué",
    "es","son","de","la","el","y","o","en","un","al","se","su","sus","necesito",
    "puede","podria","podría","me","mi","tu","hay","mas","más","sin","esta","este",
    "esto","ser","hacer","cual","cuál","cuanto","cuánto"
}

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^\wáéíóúñü]+", " ", text, flags=re.UNICODE)
    return text

def extract_file(uploaded):
    name = uploaded.name
    data = uploaded.getvalue()
    ext = name.lower().rsplit(".", 1)[-1]
    pages = []
    if ext == "pdf":
        reader = PdfReader(BytesIO(data))
        for i, page in enumerate(reader.pages, start=1):
            pages.append((f"{name} · página {i}", page.extract_text() or ""))
    elif ext == "docx":
        doc = Document(BytesIO(data))
        pages.append((name, "\n".join(p.text for p in doc.paragraphs)))
        for ti, table in enumerate(doc.tables, start=1):
            rows = [" | ".join(cell.text for cell in row.cells) for row in table.rows]
            pages.append((f"{name} · tabla {ti}", "\n".join(rows)))
    elif ext in {"txt", "md", "csv"}:
        pages.append((name, data.decode("utf-8", errors="ignore")))
    else:
        raise ValueError("Formato no admitido. Utiliza PDF, DOCX, TXT, MD o CSV.")

    chunks = []
    for source, content in pages:
        content = re.sub(r"\s+", " ", content).strip()
        if not content:
            continue
        # Chunks de aproximadamente 1.000 caracteres con solapamiento.
        size, overlap = 1000, 150
        start = 0
        while start < len(content):
            part = content[start:start + size]
            if part.strip():
                chunks.append({"source": source, "text": part})
            start += size - overlap
    return chunks

def retrieve_chunks(question, chunks, limit=5):
    terms = {
        t for t in normalize(question).split()
        if len(t) > 2 and t not in STOPWORDS
    }
    if not terms:
        return []
    scored = []
    for chunk in chunks:
        body = normalize(chunk["text"])
        score = sum(body.count(term) for term in terms)
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]

def extract_web_sources(response):
    results, seen = [], set()
    try:
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            metadata = getattr(candidate, "grounding_metadata", None)
            grounding_chunks = getattr(metadata, "grounding_chunks", None) or []
            for chunk in grounding_chunks:
                web = getattr(chunk, "web", None)
                if not web:
                    continue
                url = getattr(web, "uri", None)
                title = getattr(web, "title", None) or "Fuente web"
                if url and url not in seen:
                    seen.add(url)
                    results.append({"title": title, "url": url})
    except Exception:
        pass
    return results

st.markdown("""
<style>
.block-container{max-width:1120px;padding-top:1.5rem}
.mant-head{background:linear-gradient(120deg,#123452,#23679a);color:white;padding:25px 28px;border-radius:18px;margin-bottom:14px}
.mant-head h1{font-size:2.15rem;margin:0}.mant-head p{font-size:1.08rem;margin:6px 0 0}
.warning{background:#fff8e7;border:1px solid #f1dfb5;color:#6c551e;padding:13px 16px;border-radius:8px;margin-bottom:18px}
.small-note{color:#64748b;font-size:.88rem}
</style>
<div class="mant-head"><h1>🛠️ MANTENIA</h1>
<p>Asistente Virtual de Mantenimiento de Equipos Mineros</p>
<span>IA generativa Gemini · Google Search · Base documental RAG</span></div>
<div class="warning"><b>Importante:</b> las respuestas son orientativas. No sustituyen manuales OEM,
procedimientos de seguridad, IPERC, permisos de trabajo ni la evaluación de personal competente.</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Fuentes de conocimiento")
    st.markdown("**1. Búsqueda en Internet**")
    use_web = st.toggle("Activar Google Search", value=True)
    st.caption("Gemini puede consultar páginas web y devolver enlaces de las fuentes encontradas.")
    st.divider()
    st.markdown("**2. Base documental propia**")
    uploads = st.file_uploader(
        "Carga manuales y procedimientos",
        type=["pdf", "docx", "txt", "md", "csv"],
        accept_multiple_files=True,
        help="Los documentos se procesan en memoria para esta sesión de la aplicación."
    )
    if "doc_chunks" not in st.session_state:
        st.session_state.doc_chunks = []
    if st.button("Procesar documentos", use_container_width=True, disabled=not uploads):
        all_chunks = []
        errors = []
        for uploaded in uploads or []:
            try:
                all_chunks.extend(extract_file(uploaded))
            except Exception as exc:
                errors.append(f"{uploaded.name}: {exc}")
        st.session_state.doc_chunks = all_chunks
        if all_chunks:
            st.success(f"Documentos procesados: {len(all_chunks)} fragmentos.")
        for error in errors:
            st.warning(error)
    if st.session_state.doc_chunks:
        st.success(f"Base documental activa: {len(st.session_state.doc_chunks)} fragmentos")
        st.caption("Vuelve a cargar y procesar los archivos si se reinicia la sesión.")
    else:
        st.info("Carga PDF/DOCX y pulsa «Procesar documentos».")
    st.divider()
    st.markdown("**Temas disponibles**")
    st.markdown(
        "- Mantenimiento preventivo, correctivo y predictivo\n"
        "- Planificación y programación\n"
        "- MTBF, MTTR y disponibilidad\n"
        "- Órdenes de trabajo y backlog\n"
        "- Confiabilidad, criticidad y RCA\n"
        "- Lubricación e ISO 55001 / ISO 14224"
    )
    st.caption(f"Modelo configurado: {MODEL}")

if not GEMINI_API_KEY:
    st.error("Falta configurar GEMINI_API_KEY en Streamlit → App settings → Secrets.")
    st.info("Obtén una clave en https://aistudio.google.com/app/apikey")
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "¡Hola! Soy MANTENIA. Puedo responder consultas de mantenimiento con IA generativa, búsqueda en Internet y los manuales que cargues en la barra lateral. ¿Qué deseas consultar?"
    }]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("web_sources"):
            with st.expander("Fuentes de Internet"):
                for source in msg["web_sources"]:
                    st.markdown(f"- [{source['title']}]({source['url']})")
        if msg.get("doc_sources"):
            with st.expander("Documentos utilizados"):
                for source in msg["doc_sources"]:
                    st.markdown(f"- {source}")

suggestions = [
    "¿Cómo se calcula el MTBF y qué datos necesito?",
    "¿Cuál es la diferencia entre planificación y programación?",
    "¿Qué debe contener una orden de trabajo?",
    "¿Cómo realizar un análisis de causa raíz de una falla?",
]
cols = st.columns(4)
for col, question in zip(cols, suggestions):
    if col.button(question, use_container_width=True):
        st.session_state.pending_question = question

prompt = st.chat_input("Escribe tu consulta sobre mantenimiento...")
if not prompt and st.session_state.get("pending_question"):
    prompt = st.session_state.pop("pending_question")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("MANTENIA está consultando Gemini y las fuentes disponibles..."):
            try:
                relevant = retrieve_chunks(prompt, st.session_state.doc_chunks)
                doc_context = ""
                doc_sources = []
                if relevant:
                    doc_context = "\n\nEXTRACTOS DE DOCUMENTOS CARGADOS (prioriza estos datos cuando respondas):\n"
                    for item in relevant:
                        doc_context += f"\n[Documento: {item['source']}]\n{item['text']}\n"
                        if item["source"] not in doc_sources:
                            doc_sources.append(item["source"])
                web_context = (
                    "Utiliza Google Search para buscar información web pertinente y actualizada. "
                    "Incluye enlaces y distingue esas fuentes de los documentos del usuario."
                    if use_web else
                    "No utilices búsqueda web. Responde solo con conocimiento general y los extractos documentales disponibles."
                )
                full_prompt = (
                    f"{SYSTEM_INSTRUCTIONS}\n\n{web_context}\n"
                    f"{doc_context}\n\nCONSULTA DEL USUARIO:\n{prompt}"
                )
                config = types.GenerateContentConfig(
                    temperature=0.25,
                    max_output_tokens=1800,
                    tools=[types.Tool(google_search=types.GoogleSearch())] if use_web else None,
                )
                response = client.models.generate_content(
                    model=MODEL,
                    contents=full_prompt,
                    config=config,
                )
                answer = response.text or "Gemini no devolvió texto. Intenta reformular la consulta."
                web_sources = extract_web_sources(response) if use_web else []
                st.markdown(answer)
                if web_sources:
                    with st.expander("Fuentes de Internet"):
                        for source in web_sources:
                            st.markdown(f"- [{source['title']}]({source['url']})")
                if doc_sources:
                    with st.expander("Documentos utilizados"):
                        for source in doc_sources:
                            st.markdown(f"- {source}")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "web_sources": web_sources,
                    "doc_sources": doc_sources,
                })
            except Exception as exc:
                message = (
                    "No se pudo completar la consulta. Revisa la clave de Gemini, "
                    "el modelo, la conexión y los límites de uso de Google AI Studio. "
                    f"Detalle: {exc}"
                )
                st.error(message)
                st.session_state.messages.append({"role": "assistant", "content": message})

st.divider()
st.markdown(
    '<div class="small-note">MANTENIA combina Gemini, Google Search opcional y recuperación '
    'documental local en la sesión. Verifica siempre la información técnica con fuentes OEM '
    'y procedimientos aprobados.</div>',
    unsafe_allow_html=True
)

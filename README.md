# MANTENIA – Chatbot generativo con base documental (RAG)

## Plataforma
- **OpenAI API – Responses API + File Search:** genera respuestas y recupera fragmentos relevantes de documentos indexados en un vector store.
- **Streamlit:** interfaz web y carga de documentos.
- **Streamlit Community Cloud:** opción de publicación pública mediante GitHub.

La búsqueda de archivos de OpenAI permite recuperar información de archivos indexados mediante búsqueda semántica y por palabras clave. La aplicación utiliza un vector store para guardar la base documental. Consulte la documentación oficial:
- https://developers.openai.com/api/docs/guides/tools-file-search
- https://developers.openai.com/api/docs/guides/file-inputs

## Formatos admitidos por MANTENIA
- PDF
- DOCX
- XLSX
- CSV
- TXT
- MD

Los archivos Excel y CSV se convierten a Markdown tabular antes de indexarse. Esto permite búsquedas semánticas sobre sus filas y datos textuales, pero no sustituye un análisis estadístico avanzado ni garantiza cálculos complejos sobre grandes volúmenes.

**Importante:** los PDF escaneados sin capa de texto pueden no indexarse correctamente. Se recomienda aplicar OCR o guardar una versión PDF con texto seleccionable. Los diagramas e imágenes incrustadas en DOCX/XLSX no se extraen mediante esta conversión. Para conservarlos, convierta el documento a PDF y revise el resultado.

## Ejecutar localmente en Windows
1. Instale Python 3.10 o superior.
2. Descomprima el proyecto y abra PowerShell en la carpeta.
3. Cree entorno: `py -m venv .venv`
4. Active: `.venv\Scripts\Activate.ps1`
5. Instale: `pip install -r requirements.txt`
6. Configure la clave API en la sesión: `$env:OPENAI_API_KEY="TU_CLAVE_API"`
7. Ejecute: `streamlit run app.py`
8. Abra la dirección local que indique Streamlit.

## Crear y utilizar la base documental
1. Abra MANTENIA en el navegador.
2. En el panel lateral, pulse **Crear base documental**.
3. Copie el identificador del vector store que muestra la aplicación.
4. Guarde ese identificador como secreto `MANTENIA_VECTOR_STORE_ID` para conservar la base entre sesiones.
5. Seleccione PDF, DOCX, XLSX, CSV, TXT o MD.
6. Pulse **Agregar documentos a la base** y espere a que se complete la indexación.
7. Haga preguntas específicas sobre el contenido cargado.

Para consultas basadas en archivos, la aplicación activa la herramienta `file_search` de la Responses API sobre el vector store seleccionado.

## Secretos en Streamlit Community Cloud
En la configuración de la aplicación, agregue:
```toml
OPENAI_API_KEY = "TU_CLAVE_API"
MANTENIA_VECTOR_STORE_ID = "vs_xxxxxxxxx"
OPENAI_MODEL = "gpt-5.5"
```
No suba claves al repositorio ni las escriba en el código. Proteja el repositorio y la aplicación si los documentos contienen información interna.

## Publicación
1. Cree un repositorio GitHub privado si los documentos/código contienen información interna.
2. Suba app.py, knowledge_base.md, requirements.txt y README.md.
3. Entre a https://share.streamlit.io/ y conecte GitHub.
4. Cree una aplicación apuntando a `app.py`.
5. Configure los secretos anteriores en Streamlit.
6. Despliegue y pruebe el enlace. No publique documentos confidenciales en un sitio abierto.

## Privacidad y seguridad
- Anonimice nombres, placas, números de serie, datos personales, datos de clientes, contratos y costos sensibles antes de cargar archivos.
- Use documentos autorizados para compartir con el proveedor de API.
- Limite el acceso a la aplicación y al vector store.
- Revise las políticas de retención, acceso y tratamiento de datos de la organización y del proveedor antes de usar información operacional.
- El chatbot puede cometer errores; toda recomendación técnica debe contrastarse con manuales OEM, procedimientos aprobados y personal competente.

## Limitaciones de la versión
- Es un prototipo académico; requiere clave API válida y puede generar costos de API.
- La base documental se crea en la cuenta/proyecto OpenAI asociado a la clave.
- El identificador del vector store debe guardarse como secreto para reutilizar la misma base en despliegues o sesiones nuevas.
- La conversión de XLSX/CSV indexa texto tabular; no equivale a ejecutar consultas SQL ni análisis de datos exhaustivo.
- No se conecta a CMMS/EAM, telemetría, inventarios ni sistemas empresariales.
- No incluye autenticación de usuarios ni control de permisos por documento; antes de un uso empresarial deben añadirse.

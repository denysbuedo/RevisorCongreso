
import os
import subprocess
import requests
from docx import Document
from bs4 import BeautifulSoup
import re
from langdetect import detect

CARPETA_TRABAJOS = "./trabajos"
CARPETA_REPORTES = "./reportes"
CARPETA_REVISADOS = "./trabajos_revisados"
URL_LT = "http://localhost:8010/v2/check"

def convertir_doc_a_docx():
    print("▶ Convirtiendo archivos .doc a .docx (si existen)...")
    for archivo in os.listdir(CARPETA_TRABAJOS):
        if archivo.lower().endswith(".doc"):
            origen = os.path.join(CARPETA_TRABAJOS, archivo)
            subprocess.run([
                "libreoffice", "--headless", "--convert-to", "docx", origen, "--outdir", CARPETA_TRABAJOS
            ])

def es_palabra_inglesa(palabra):
    try:
        return detect(palabra) == "en"
    except:
        return False

def revisar_ortografia(texto):
    errores = []
    try:
        response = requests.post(URL_LT, data={"text": texto, "language": "es"})
        data = response.json()
        for match in data.get("matches", []):
            ctx = match.get("context", {})
            text = ctx.get("text", "")
            off = ctx.get("offset", 0)
            length = ctx.get("length", 0)
            palabra = text[off:off+length].strip()
            if not palabra or es_palabra_inglesa(palabra.lower()):
                continue
            errores.append({
                "message": match.get("message"),
                "context": ctx
            })
    except Exception as e:
        errores.append({
            "message": f"Error de conexión con LanguageTool: {e}",
            "context": {"text": "", "offset": 0, "length": 0}
        })
    return errores

def validar_estructura(texto):
    reglas = [
        ("Título en mayúscula y ≤ 15 palabras", texto.splitlines()[0].isupper() and len(texto.splitlines()[0].split()) <= 15),
        ("Autores y correos electrónicos presentes", "@" in texto),
        ("Resumen ≤ 250 palabras", "resumen" in texto.lower() and len(texto.split()) < 500),
        ("Palabras clave en español", "palabras clave" in texto.lower()),
        ("Traducción al inglés (título, resumen, palabras clave)", "abstract" in texto.lower()),
        ("Sección INTRODUCCIÓN", "introducción" in texto.lower()),
        ("Sección RESULTADOS o DESARROLLO", "resultados" in texto.lower() or "desarrollo" in texto.lower()),
        ("Sección CONCLUSIONES", "conclusiones" in texto.lower()),
        ("Sección REFERENCIAS BIBLIOGRÁFICAS", "referencias" in texto.lower()),
    ]
    return reglas

def validar_formato(texto):
    errores = []
    if "Verdana" not in texto:
        errores.append("Fuente incorrecta: no se detecta 'Verdana'")
    if "\t" in texto:
        errores.append("Uso de tabuladores detectado")
    if "left" in texto.lower():
        errores.append("Texto no justificado")
    return errores

def validar_referencias(texto):
    refs = []
    for linea in texto.splitlines():
        if any(pal in linea.lower() for pal in [str(y) for y in range(2000, 2026)] + ["doi", "http"]):
            cumple = bool(re.search(r"[A-Z][a-z]+, [A-Z]\.", linea)) and bool(re.search(r"\(\d{4}\)", linea))
            refs.append((linea.strip(), cumple))
    return refs

def generar_html(nombre_archivo, estructura, ortografia, formato, referencias):
    html = BeautifulSoup("<html><head><meta charset='utf-8'><title>Reporte</title></head><body></body></html>", "html.parser")
    body = html.body
    titulo = html.new_tag("h1")
    titulo.string = "📘 Informe del revisar Automático del Congreso Universidad 2026"
    body.append(titulo)

    subtitulo = html.new_tag("h2")
    subtitulo.string = f"📄 Archivo revisado: {nombre_archivo}"
    body.append(subtitulo)

    # Estructura
    body.append(html.new_tag("h2", string="I. 📚 Estructura del manuscrito"))
    ul1 = html.new_tag("ul")
    for item, ok in estructura:
        li = html.new_tag("li")
        li.string = f"{'✅' if ok else '❌'} {item}"
        ul1.append(li)
    body.append(ul1)

    # Ortografía
    body.append(html.new_tag("h2", string="II. 📝 Revisión ortográfica y gramatical"))
    ul2 = html.new_tag("ul")
    for err in ortografia:
        ctx = err["context"]
        msg = err["message"]
        text = ctx.get("text", "")
        off = ctx.get("offset", 0)
        length = ctx.get("length", 0)
        palabra = text[off:off+length]
        resaltado = f"{text[:off]}<mark>{palabra}</mark>{text[off+length:]}"
        li = html.new_tag("li")
        li.append(html.new_tag("strong", string=f"{palabra}: "))
        li.append(msg)
        p = html.new_tag("p")
        p.append(BeautifulSoup(resaltado, "html.parser"))
        li.append(p)
        ul2.append(li)
    body.append(ul2)

    # Formato
    body.append(html.new_tag("h2", string="III. 📐 Formato del documento"))
    ul3 = html.new_tag("ul")
    for err in formato:
        li = html.new_tag("li")
        li.string = f"❌ {err}"
        ul3.append(li)
    body.append(ul3)

    # APA
    body.append(html.new_tag("h2", string="IV. 📖 Revisión básica de estilo APA"))
    ul4 = html.new_tag("ul")
    for ref, ok in referencias:
        li = html.new_tag("li")
        li.string = f"{'✅' if ok else '❌'} {ref}"
        ul4.append(li)
    body.append(ul4)

    os.makedirs(CARPETA_REPORTES, exist_ok=True)
    with open(os.path.join(CARPETA_REPORTES, f"{nombre_archivo}.html"), "w", encoding="utf-8") as f:
        f.write(str(html.prettify()))

def procesar_trabajos():
    convertir_doc_a_docx()
    os.makedirs(CARPETA_REPORTES, exist_ok=True)
    os.makedirs(CARPETA_REVISADOS, exist_ok=True)

    for archivo in os.listdir(CARPETA_TRABAJOS):
        if archivo.endswith(".docx"):
            ruta = os.path.join(CARPETA_TRABAJOS, archivo)
            doc = Document(ruta)
            texto = "\n".join([p.text for p in doc.paragraphs])

            estructura = validar_estructura(texto)
            ortografia = revisar_ortografia(texto)
            formato = validar_formato(texto)
            referencias = validar_referencias(texto)

            nombre = os.path.splitext(archivo)[0]
            generar_html(nombre, estructura, ortografia, formato, referencias)

            os.rename(ruta, os.path.join(CARPETA_REVISADOS, archivo))

if __name__ == "__main__":
    procesar_trabajos()

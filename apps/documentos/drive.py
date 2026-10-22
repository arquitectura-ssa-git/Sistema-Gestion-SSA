"""Enlaces de Google Drive: en lugar de subir el archivo, el documento guarda el enlace y lo muestra con la vista
previa de Google. Quién puede abrirlo lo decide Drive (con quién está compartido); SOPHIA decide a quién le
muestra el enlace."""

import re
from urllib.parse import parse_qs, urlparse

HOSTS = ("drive.google.com", "docs.google.com")
DOCS = {"document": "Documento de Google", "spreadsheets": "Hoja de cálculo de Google",
        "presentation": "Presentación de Google", "drawings": "Dibujo de Google", "forms": "Formulario de Google"}


def analizar(enlace):
    """Devuelve {"clase": archivo|carpeta|documento, "id", "vista_previa", "descripcion"} o None si no es de Drive."""
    try:
        url = urlparse((enlace or "").strip())
    except ValueError:
        return None
    if url.scheme != "https" or url.hostname not in HOSTS:
        return None
    partes = [p for p in url.path.split("/") if p]
    consulta = parse_qs(url.query)

    if url.hostname == "docs.google.com":
        # /document/d/ID/edit, /spreadsheets/d/ID/..., /presentation/d/ID/...
        if len(partes) >= 3 and partes[0] in DOCS and partes[1] == "d":
            return {"clase": "documento", "id": partes[2], "descripcion": DOCS[partes[0]], "google": partes[0],
                    "vista_previa": f"https://docs.google.com/{partes[0]}/d/{partes[2]}/preview"}
        return None

    # drive.google.com
    if "folders" in partes:
        ident = partes[partes.index("folders") + 1] if partes.index("folders") + 1 < len(partes) else ""
        if ident:
            return {"clase": "carpeta", "id": ident, "descripcion": "Carpeta de Drive",
                    "vista_previa": f"https://drive.google.com/embeddedfolderview?id={ident}#grid"}
    if len(partes) >= 3 and partes[0] == "file" and partes[1] == "d":
        ident = partes[2]
    else:
        ident = (consulta.get("id") or [""])[0]
    if ident and re.fullmatch(r"[\w-]{10,}", ident):
        return {"clase": "archivo", "id": ident, "descripcion": "Archivo de Drive",
                "vista_previa": f"https://drive.google.com/file/d/{ident}/preview"}
    return None

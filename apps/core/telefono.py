"""Teléfonos con un solo formato: país (+54 por defecto), característica y número → «+54 381 300-4288»."""

import re

from django import forms

PAIS = "+54"
# Características de 3 cifras más usadas (el resto se toma de 4; Buenos Aires es 11)
TRES_CIFRAS = {"221", "223", "236", "237", "249", "260", "261", "263", "264", "266", "280", "291", "294", "297",
               "299", "336", "341", "342", "343", "345", "348", "351", "353", "358", "362", "364", "370", "376",
               "379", "380", "381", "383", "385", "387", "388"}


def formatear(pais, area, numero):
    numero = re.sub(r"\D", "", numero or "")
    area = re.sub(r"\D", "", area or "")
    if not numero:
        return ""
    pais = "+" + re.sub(r"\D", "", pais or PAIS) if re.sub(r"\D", "", pais or "") else PAIS
    if len(numero) > 4:
        numero = f"{numero[:-4]}-{numero[-4:]}"
    return " ".join(p for p in (pais, area, numero) if p)


def separar(texto):
    """De lo que haya cargado (con o sin +54, 9, 0 o 15) a (país, característica, número). None si no se entiende."""
    if not texto:
        return (PAIS, "", "")
    partes = texto.split()
    if len(partes) == 3 and partes[0].startswith("+"):  # ya está en el formato
        return partes[0], partes[1], partes[2].replace("-", "")
    digitos = re.sub(r"\D", "", texto)
    pais = PAIS
    if texto.strip().startswith("+") and not digitos.startswith("54"):
        return None  # otro país: se deja como está
    if digitos.startswith("54"):
        digitos = digitos[2:]
    if digitos.startswith("9") and len(digitos) == 11:
        digitos = digitos[1:]  # el 9 de los celulares en WhatsApp
    digitos = digitos.lstrip("0")
    if len(digitos) == 12 and digitos[3:5] == "15":  # 381 15 4xxxxxx
        digitos = digitos[:3] + digitos[5:]
    if len(digitos) != 10:
        return None
    largo = 2 if digitos.startswith("11") else 3 if digitos[:3] in TRES_CIFRAS else 4
    return pais, digitos[:largo], digitos[largo:]


def normalizar(texto):
    partes = separar(texto)
    return formatear(*partes) if partes else (texto or "")


class TelefonoWidget(forms.MultiWidget):
    template_name = "widgets/telefono.html"

    def __init__(self, attrs=None):
        widgets = [
            forms.TextInput(attrs={"placeholder": "+54", "aria-label": "País", "inputmode": "tel", "size": 4}),
            forms.TextInput(attrs={"placeholder": "381", "aria-label": "Característica", "inputmode": "numeric",
                                   "size": 5}),
            forms.TextInput(attrs={"placeholder": "3004288", "aria-label": "Número", "inputmode": "numeric"}),
        ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        partes = separar(value) if value else (PAIS, "", "")
        return list(partes) if partes else ["", "", value]


class TelefonoField(forms.MultiValueField):
    widget = TelefonoWidget

    def __init__(self, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("help_text", "País (+54), característica sin 0 y número sin 15.")
        campos = (forms.CharField(required=False), forms.CharField(required=False), forms.CharField(required=False))
        super().__init__(campos, require_all_fields=False, **kwargs)
        self.initial = [PAIS, "", ""]

    def compress(self, valores):
        pais, area, numero = (valores + ["", "", ""])[:3] if valores else ("", "", "")
        if not re.sub(r"\D", "", numero or ""):
            return ""
        if re.sub(r"[\d\s-]", "", (area or "") + (numero or "")):
            raise forms.ValidationError("Usá solo números en la característica y el número.")
        area, numero = re.sub(r"\D", "", area or "").lstrip("0"), re.sub(r"\D", "", numero)
        if not area:
            raise forms.ValidationError("Falta la característica (ej.: 381).")
        if re.sub(r"\D", "", pais or PAIS) == "54":
            if len(area + numero) == 12 and numero.startswith("15"):
                numero = numero[2:]  # el 15 de los celulares no va
            if len(area + numero) != 10:
                raise forms.ValidationError(
                    "En Argentina la característica y el número suman 10 cifras (ej.: 381 + 3004288).")
        return formatear(pais, area, numero)

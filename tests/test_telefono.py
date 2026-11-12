import pytest

from apps.agenda.models import Contacto
from apps.core.telefono import TelefonoField, normalizar
from apps.cuentas.forms import ClienteForm


@pytest.mark.parametrize("cargado,esperado", [
    ("+5493814001122", "+54 381 400-1122"),
    ("381 15 4001122", "+54 381 400-1122"),
    ("0381-4001122", "+54 381 400-1122"),
    ("+54 9 11 2233-4455", "+54 11 2233-4455"),
    ("3863401234", "+54 3863 40-1234"),
    ("+1 555 1234", "+1 555 1234"),
    ("4221100", "4221100"),  # incompleto: queda como estaba
])
def test_normalizar(cargado, esperado):
    assert normalizar(cargado) == esperado


def test_campo_arma_el_formato():
    f = TelefonoField()
    assert f.clean(["+54", "381", "4001122"]) == "+54 381 400-1122"
    assert f.clean(["", "11", "22334455"]) == "+54 11 2233-4455"
    assert f.clean(["+54", "", ""]) == ""


def test_campo_pide_caracteristica():
    from django import forms
    with pytest.raises(forms.ValidationError):
        TelefonoField().clean(["+54", "", "4001122"])


def test_campo_saca_el_0_y_el_15_y_controla_las_cifras():
    from django import forms
    assert TelefonoField().clean(["+54", "0381", "15-4001122"]) == "+54 381 400-1122"
    with pytest.raises(forms.ValidationError):
        TelefonoField().clean(["+54", "381", "40011"])


@pytest.mark.django_db
def test_cliente_se_guarda_con_formato_y_pasa_a_la_agenda():
    form = ClienteForm(data={"apellido": "Gómez", "nombres": "ana", "telefono_0": "+54", "telefono_1": "381",
                             "telefono_2": "300 4288"})
    assert form.is_valid(), form.errors
    cliente = form.save()
    assert cliente.telefono == "+54 381 300-4288"
    assert Contacto.objects.get(cliente=cliente).telefono == "+54 381 300-4288"


def test_el_formulario_muestra_tres_casilleros():
    html = ClienteForm(initial={"telefono": "+5493814001122"})["telefono"].as_widget()
    assert 'name="telefono_0"' in html and 'value="+54"' in html
    assert 'value="381"' in html and 'value="4001122"' in html

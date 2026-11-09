"""Ayuda: video del Time Report y preguntas frecuentes para todo el personal."""

from django.contrib.staticfiles import finders

from apps.core.ayuda import bloques

from .conftest import cliente_de


def test_el_personal_ve_la_ayuda_y_el_menu(comun):
    html = cliente_de(comun).get("/ayuda/").content.decode()
    assert "cargar-time-report.mp4" in html and "¿Cómo cargo mis horas?" in html
    assert 'href="/ayuda/"' in cliente_de(comun).get("/tablero/").content.decode()


def test_el_video_y_su_portada_existen():
    assert finders.find("ayuda/cargar-time-report.mp4") and finders.find("ayuda/cargar-time-report.jpg")


def test_las_respuestas_admiten_listas():
    assert bloques("Hacé esto:\n- uno\n- dos\n\nListo.") == [
        {"tipo": "p", "texto": "Hacé esto:"}, {"tipo": "lista", "items": ["uno", "dos"]}, {"tipo": "p", "texto": "Listo."}]


def test_los_dos_videos_estan_en_la_pagina(comun):
    html = cliente_de(comun).get("/ayuda/").content.decode()
    for archivo in ("cargar-time-report", "crear-proyecto", "avance-y-tareas"):
        assert f"ayuda/{archivo}.mp4" in html and finders.find(f"ayuda/{archivo}.mp4")
    assert "¿Quién puede crear un proyecto u obra?" in html

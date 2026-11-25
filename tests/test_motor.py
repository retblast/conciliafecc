"""Pruebas del motor con Excel sintéticos. Sin datos personales ni archivos reales."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from conciliafecc.contracts import EngineInputError, Source, Workbooks
from conciliafecc.motor import CONFIGURACION_PRODUCCION, Conciliador, FuenteConfig

CABECERA = ("Apellidos", "Nombres", "N° Matrícula", "Programa", "Grado/Título")


def _xlsx(hoja: str, filas: list[tuple], con_espacio_cabecera: bool = False) -> bytes:
	book = Workbook()
	sheet = book.active
	sheet.title = hoja
	if con_espacio_cabecera:
		sheet.append(())
	for fila in filas:
		sheet.append(fila)
	buffer = BytesIO()
	book.save(buffer)
	book.close()
	return buffer.getvalue()


def _ura(filas: list[tuple]) -> bytes:
	return _xlsx("Worksheet", filas, con_espacio_cabecera=True)


def _biblioteca(filas: list[tuple]) -> bytes:
	return _xlsx("Worksheet", filas, con_espacio_cabecera=True)


def _no_adeudos(filas: list[tuple]) -> bytes:
	return _xlsx("Hoja1", filas)


def _workbooks(ura: bytes, biblioteca: bytes, no_adeudos: bytes) -> Workbooks:
	return Workbooks(ura=ura, biblioteca=biblioteca, no_adeudos=no_adeudos)


def _fila(apellido: str, nombre: str, matricula: object) -> tuple:
	return (apellido, nombre, matricula, "Programa", "Grado")


def test_interseccion_de_tres_aprueba_y_totales_derivados():
	comunes = [
		CABECERA,
		_fila("Pérez", "Ana", "1000000001"),
		_fila("López", "Beto", "1000000002"),
	]
	resultado = Conciliador().reconcile(
		_workbooks(
			_ura(comunes),
			_biblioteca(comunes),
			_no_adeudos([_fila("Pérez", "Ana", "1000000001")]),
		)
	)
	por_referencia = {persona.referencia: persona for persona in resultado.personas}

	assert resultado.aprobados == 1
	assert resultado.registros_por_fuente.ura == 2
	assert resultado.registros_por_fuente.biblioteca == 2
	assert resultado.registros_por_fuente.no_adeudos == 1
	assert resultado.faltantes_por_fuente.no_adeudos == 1
	assert por_referencia["P0001"].aprobada
	assert por_referencia["P0001"].faltantes == []
	assert por_referencia["P0002"].faltantes == [Source.CLEARANCE]
	assert all("1000000001" not in referencia for referencia in por_referencia)


def test_numero_y_texto_coinciden_pero_los_ceros_no_se_recortan():
	resultado = Conciliador().reconcile(
		_workbooks(
			_ura([
				CABECERA,
				_fila("Pérez", "Ana", 1000000001),
				_fila("García", "Luis", "001000000003"),
			]),
			_biblioteca([
				CABECERA,
				_fila("Pérez", "Ana", "1000000001"),
				_fila("García", "Luis", "001000000003"),
			]),
			_no_adeudos([
				_fila("Pérez", "Ana", "1000000001"),
				_fila("García", "Luis", "1000000003"),
			]),
		)
	)
	por_faltantes = {tuple(persona.faltantes): persona for persona in resultado.personas}

	assert len(resultado.personas) == 3
	assert resultado.aprobados == 1
	assert any(
		persona.aprobada and persona.faltantes == []
		for persona in resultado.personas
	)
	assert por_faltantes[(Source.CLEARANCE,)].faltantes == [Source.CLEARANCE]
	assert por_faltantes[(Source.URA, Source.LIBRARY)].faltantes == [
		Source.URA,
		Source.LIBRARY,
	]


def test_duplicado_en_una_fuente_bloquea_la_aprobacion():
	resultado = Conciliador().reconcile(
		_workbooks(
			_ura([
				CABECERA,
				_fila("Pérez", "Ana", "1000000001"),
				_fila("Pérez", "Ana", "1000000001"),
			]),
			_biblioteca([CABECERA, _fila("Pérez", "Ana", "1000000001")]),
			_no_adeudos([_fila("Pérez", "Ana", "1000000001")]),
		)
	)

	assert resultado.registros_por_fuente.ura == 2
	assert resultado.aprobados == 0
	assert resultado.personas[0].duplicados == [Source.URA]
	assert any("duplicado en ura" in texto
	           for texto in resultado.personas[0].inconsistencias)


def test_persona_ausente_de_dos_fuentes():
	resultado = Conciliador().reconcile(
		_workbooks(
			_ura([CABECERA, _fila("Pérez", "Ana", "1000000001")]),
			_biblioteca([CABECERA, _fila("López", "Beto", "1000000002")]),
			_no_adeudos([_fila("García", "Luis", "1000000003")]),
		)
	)

	assert resultado.aprobados == 0
	assert [persona.faltantes for persona in resultado.personas] == [
		[Source.LIBRARY, Source.CLEARANCE],
		[Source.URA, Source.CLEARANCE],
		[Source.URA, Source.LIBRARY],
	]


def test_filas_sin_clave_e_identificadores_invalidos_se_omiten_y_avisan():
	resultado = Conciliador().reconcile(
		_workbooks(
			_ura([
				CABECERA,
				_fila("Sin", "Clave", ""),
				_fila("Invalido", "Dato", "ABC123"),
				_fila("Válido", "Persona", "1000000005"),
			]),
			_biblioteca([CABECERA, _fila("Válido", "Persona", "1000000005")]),
			_no_adeudos([_fila("Válido", "Persona", "1000000005")]),
		)
	)

	assert resultado.registros_por_fuente.ura == 1
	assert resultado.aprobados == 1
	assert any("sin matrícula" in aviso for aviso in resultado.advertencias)
	assert any("inválido" in aviso for aviso in resultado.advertencias)


def test_nombres_discrepantes_son_inconsistencia_y_no_aprueban():
	resultado = Conciliador().reconcile(
		_workbooks(
			_ura([CABECERA, _fila("Pérez", "Ana", "1000000007")]),
			_biblioteca([CABECERA, _fila("Pérez", "Ana María", "1000000007")]),
			_no_adeudos([_fila("Pérez", "Ana", "1000000007")]),
		)
	)

	assert resultado.aprobados == 0
	assert any("nombres no coinciden" in texto
	           for texto in resultado.personas[0].inconsistencias)


def test_hoja_ausente_se_atribuye_a_la_fuente():
	configuracion = {fuente: CONFIGURACION_PRODUCCION[fuente] for fuente in Source}
	configuracion[Source.LIBRARY] = replace(
		configuracion[Source.LIBRARY], hoja="Worksheet"
	)
	workbooks = _workbooks(
		_ura([CABECERA, _fila("Pérez", "Ana", "1000000009")]),
		_xlsx("Otra", [CABECERA, _fila("Pérez", "Ana", "1000000009")], True),
		_no_adeudos([_fila("Pérez", "Ana", "1000000009")]),
	)

	with pytest.raises(EngineInputError) as capturado:
		Conciliador(configuracion).reconcile(workbooks)
	assert capturado.value.source == Source.LIBRARY


def test_cabecera_ausente_se_atribuye_a_la_fuente():
	cabecera_ajena = ("Apellidos", "Nombres", "OTRA", "Programa", "Grado/Título")
	workbooks = _workbooks(
		_ura([CABECERA, _fila("Pérez", "Ana", "1000000009")]),
		_biblioteca([cabecera_ajena, _fila("Pérez", "Ana", "1000000009")]),
		_no_adeudos([_fila("Pérez", "Ana", "1000000009")]),
	)

	with pytest.raises(EngineInputError) as capturado:
		Conciliador().reconcile(workbooks)
	assert capturado.value.source == Source.LIBRARY


def test_no_hace_coincidencias_aproximadas():
	resultado = Conciliador().reconcile(
		_workbooks(
			_ura([CABECERA, _fila("Pérez", "Ana", "1000000011")]),
			_biblioteca([CABECERA, _fila("Pérez", "Ana", "1000000012")]),
			_no_adeudos([_fila("Pérez", "Ana", "1000000011")]),
		)
	)

	assert len(resultado.personas) == 2
	assert resultado.aprobados == 0
	assert [persona.faltantes for persona in resultado.personas] == [
		[Source.LIBRARY],
		[Source.URA, Source.CLEARANCE],
	]


def test_configuracion_sin_cabecera_exige_indices():
	with pytest.raises(TypeError, match="índice"):
		FuenteConfig(fila_cabecera=None, columna_clave="MATRÍCULA")


def test_motor_no_importa_la_api():
	raiz = Path(__file__).resolve().parents[1]
	entorno = dict(os.environ)
	PYTHONPATH = os.pathsep.join(
		filter(None, (str(raiz), entorno.get("PYTHONPATH", "")))
	)
	entorno["PYTHONPATH"] = PYTHONPATH
	comando = (
		"import conciliafecc.motor, sys; "
		"assert 'conciliafecc.api' not in sys.modules; "
		"assert 'fastapi' not in sys.modules"
	)
	terminado = subprocess.run(
		[sys.executable, "-c", comando],
		cwd=raiz, env=entorno, capture_output=True, text=True, check=False,
	)
	assert terminado.returncode == 0, terminado.stderr

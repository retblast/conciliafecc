"""Núcleo de conciliación de los tres listados de la FECC.

Este módulo no conoce HTTP: recibe los bytes originales de cada fuente y
devuelve un ``Result`` del contrato compartido. La configuración por fuente
refleja la estructura observada en los Excel institucionales: hojas ``Worksheet``
con cabecera en la fila 2 y ``Hoja1`` sin cabecera.

La regla de aprobación del MVP es presencia confirmada en las tres fuentes, sin
duplicados ni inconsistencias. El supuesto queda registrado en ``advertencias``:
los listados no traen una columna de estado y la regla aún debe ser confirmada
por las áreas.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from io import BytesIO
from unicodedata import normalize as normalizar_unicode

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from .contracts import (
	EngineInputError,
	PersonResult,
	Result,
	Source,
	SourceCounts,
	Workbooks,
)

Columna = str | int
ADVERTENCIA_APROBACION = (
	"Regla de aprobación ratificada para el MVP: presencia en las tres fuentes "
	"sin discrepancias. Pendiente de confirmación institucional."
)


@dataclass(frozen=True)
class FuenteConfig:
	"""Cómo leer una fuente. Las columnas admiten cabecera o índice 1-based."""

	hoja: str | None = None
	fila_cabecera: int | None = 1
	columna_clave: Columna = 1
	columnas_nombre: tuple[Columna, ...] = ()
	fila_inicio: int | None = None

	def __post_init__(self) -> None:
		if self.fila_cabecera is not None and self.fila_cabecera < 1:
			raise ValueError("fila_cabecera debe ser positiva.")
		if self.fila_inicio is not None and self.fila_inicio < 1:
			raise ValueError("fila_inicio debe ser positiva.")
		if self.fila_cabecera is None and not isinstance(self.columna_clave, int):
			raise TypeError("Sin cabecera, columna_clave debe ser un índice.")
		if self.fila_cabecera is None:
			for columna in self.columnas_nombre:
				if not isinstance(columna, int):
					raise TypeError("Sin cabecera, columnas_nombre deben ser índices.")

	@property
	def inicio(self) -> int:
		if self.fila_inicio is not None:
			return self.fila_inicio
		return (self.fila_cabecera + 1) if self.fila_cabecera else 1


CONFIGURACION_PRODUCCION: dict[Source, FuenteConfig] = {
	Source.URA: FuenteConfig(
		hoja="Worksheet",
		fila_cabecera=2,
		columna_clave="N° Matrícula",
		columnas_nombre=("Apellidos", "Nombres"),
	),
	Source.LIBRARY: FuenteConfig(
		hoja="Worksheet",
		fila_cabecera=2,
		columna_clave="N° Matrícula",
		columnas_nombre=("Apellidos", "Nombres"),
	),
	Source.CLEARANCE: FuenteConfig(
		hoja="Hoja1",
		fila_cabecera=None,
		columna_clave=3,
		columnas_nombre=(1, 2),
	),
}


@dataclass
class LecturaFuente:
	"""Estado agregado de una fuente. Ningún campo se serializa."""

	registros: int = 0
	por_clave: dict[str, str] = field(default_factory=dict)
	sin_clave: int = 0
	invalidas: int = 0
	duplicados: set[str] = field(default_factory=set)


def normalizar_texto(valor: object) -> str:
	"""NFKC, espacios colapsados y mayúsculas. Sin coincidencias aproximadas."""
	if valor is None:
		return ""
	texto = normalizar_unicode("NFKC", str(valor))
	return " ".join(texto.split()).upper()


def normalizar_matricula(valor: object) -> str | None:
	"""Devuelve la matrícula canónica o ``None`` si no es válida.

	Se conservan los ceros a la izquierda cuando el dato viene como texto; no se
	rellenan ni se recortan. Los números enteros ya llegaron sin ceros desde
	Excel, y el motor no puede recuperarlos sin inventar información.
	"""
	if valor is None or isinstance(valor, bool):
		return None
	if isinstance(valor, int):
		texto = str(valor)
	elif isinstance(valor, float):
		if not valor.is_integer():
			return None
		texto = str(int(valor))
	else:
		texto = normalizar_unicode("NFKC", str(valor)).strip()
	texto = "".join(texto.split())
	return texto if re.fullmatch(r"\d{8,}", texto) else None


class Conciliador:
	"""Implementación de :class:`Engine` con las reglas ratificadas del MVP."""

	def __init__(self, configuracion: Mapping[Source, FuenteConfig] | None = None):
		self.configuracion = {
			fuente: (configuracion or {}).get(fuente, CONFIGURACION_PRODUCCION[fuente])
			for fuente in Source
		}

	def reconcile(self, workbooks: Workbooks) -> Result:
		lecturas: dict[Source, LecturaFuente] = {}
		for fuente in Source:
			contenido = getattr(workbooks, fuente.value)
			try:
				lecturas[fuente] = self._leer(contenido, fuente)
			except EngineInputError:
				raise
			except Exception as error:
				raise EngineInputError(fuente) from error

		claves = sorted(
			{clave for lectura in lecturas.values() for clave in lectura.por_clave}
		)
		referencias = {clave: f"P{numero:04d}" for numero, clave in enumerate(claves, 1)}

		personas: list[PersonResult] = []
		con_nombres_discrepantes = 0
		for clave in claves:
			faltantes = [fuente for fuente in Source if clave not in lecturas[fuente].por_clave]
			duplicados = [fuente for fuente in Source if clave in lecturas[fuente].duplicados]
			inconsistencias = [
				f"Registro duplicado en {fuente.value}." for fuente in duplicados
			]

			nombres = {
				lecturas[fuente].por_clave[clave]
				for fuente in Source
				if clave in lecturas[fuente].por_clave
			}
			if len(nombres) > 1:
				con_nombres_discrepantes += 1
				inconsistencias.append("Los nombres no coinciden entre las fuentes.")

			personas.append(
				PersonResult(
					referencia=referencias[clave],
					aprobada=not faltantes and not duplicados and not inconsistencias,
					faltantes=faltantes,
					duplicados=duplicados,
					inconsistencias=inconsistencias,
				)
			)

		return Result(
			registros_por_fuente=SourceCounts(
				**{fuente.value: lecturas[fuente].registros for fuente in Source}
			),
			aprobados=sum(persona.aprobada for persona in personas),
			faltantes_por_fuente=SourceCounts(
				**{
					fuente.value: sum(fuente in persona.faltantes for persona in personas)
					for fuente in Source
				}
			),
			personas=personas,
			advertencias=self._advertencias(lecturas, con_nombres_discrepantes),
		)

	def _leer(self, contenido: bytes, fuente: Source) -> LecturaFuente:
		config = self.configuracion[fuente]
		lectura = LecturaFuente()
		book = load_workbook(
			BytesIO(contenido), read_only=True, data_only=True, keep_links=False
		)
		try:
			sheet = self._hoja(book, config, fuente)
			indice_clave = self._indice_columna(
				sheet, config.columna_clave, config, fuente
			)
			indices_nombre = tuple(
				self._indice_columna(sheet, columna, config, fuente)
				for columna in config.columnas_nombre
			)

			for fila in sheet.iter_rows(min_row=config.inicio, values_only=True):
				if not any(normalizar_texto(valor) for valor in fila):
					continue
				valor_clave = self._valor(fila, indice_clave)
				clave = normalizar_matricula(valor_clave)
				if clave is None:
					if not normalizar_texto(valor_clave):
						lectura.sin_clave += 1
					else:
						lectura.invalidas += 1
					continue

				lectura.registros += 1
				if clave in lectura.por_clave:
					lectura.duplicados.add(clave)
					continue

				nombre = " ".join(
					parte
					for indice in indices_nombre
					if (parte := normalizar_texto(self._valor(fila, indice)))
				)
				lectura.por_clave[clave] = nombre
		finally:
			book.close()

		if (
			config.fila_cabecera is None
			and lectura.registros == 0
			and lectura.sin_clave + lectura.invalidas > 0
		):
			raise EngineInputError(fuente)
		return lectura

	@staticmethod
	def _hoja(book, config: FuenteConfig, fuente: Source) -> Worksheet:
		if config.hoja is None:
			return book.active
		if config.hoja not in book.sheetnames:
			raise EngineInputError(fuente)
		return book[config.hoja]

	@staticmethod
	def _indice_columna(
		sheet: Worksheet, columna: Columna, config: FuenteConfig, fuente: Source
	) -> int:
		if isinstance(columna, int):
			if columna < 1:
				raise EngineInputError(fuente)
			return columna
		if config.fila_cabecera is None:
			raise EngineInputError(fuente)
		cabecera = [
			normalizar_texto(celda.value) for celda in sheet[config.fila_cabecera]
		]
		objetivo = normalizar_texto(columna)
		if objetivo not in cabecera:
			raise EngineInputError(fuente)
		return cabecera.index(objetivo) + 1

	@staticmethod
	def _valor(fila: Sequence[object], indice: int) -> object:
		return fila[indice - 1] if indice <= len(fila) else None

	@staticmethod
	def _advertencias(
		lecturas: Mapping[Source, LecturaFuente], con_nombres_discrepantes: int
	) -> list[str]:
		advertencias = [ADVERTENCIA_APROBACION]
		for fuente in Source:
			lectura = lecturas[fuente]
			if lectura.sin_clave:
				advertencias.append(
					f"{fuente.value}: se omitieron {lectura.sin_clave} fila(s) sin matrícula."
				)
			if lectura.invalidas:
				advertencias.append(
					f"{fuente.value}: se omitieron {lectura.invalidas} identificador(es) inválido(s)."
				)
		if con_nombres_discrepantes:
			advertencias.append(
				f"{con_nombres_discrepantes} matrícula(s) presentan nombres discrepantes entre fuentes."
			)
		return advertencias

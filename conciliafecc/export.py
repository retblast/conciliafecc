from io import BytesIO

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from .contracts import Result, Source


def append_row(sheet: Worksheet, *values: str | int | bool) -> None:
	if any(isinstance(value, str) and len(value.encode("utf-16-le")) > 2 * 32767 for value in values):
		raise ValueError("El texto supera el límite de una celda de Excel.")
	sheet.append(values)
	for cell in sheet[sheet.max_row]:
		if isinstance(cell.value, str):
			cell.data_type = "s"


def export_result(result: Result) -> bytes:
	"""Genera un libro provisional a partir del resultado de conciliación."""
	book = Workbook()
	summary = book.active
	summary.title = "Resumen"
	append_row(summary, "Fuente", "Registros", "Personas faltantes")
	for source in Source:
		append_row(
			summary, source.value,
			getattr(result.registros_por_fuente, source.value),
			getattr(result.faltantes_por_fuente, source.value),
		)
	append_row(summary, "Personas aprobadas", result.aprobados)

	people = book.create_sheet("Personas")
	append_row(people, "Referencia", "Aprobada")
	issues = book.create_sheet("Discrepancias")
	append_row(issues, "Referencia", "Tipo", "Fuente", "Detalle")
	for person in result.personas:
		append_row(people, person.referencia, person.aprobada)
		for source in person.faltantes:
			append_row(issues, person.referencia, "Faltante", source.value, "")
		for source in person.duplicados:
			append_row(issues, person.referencia, "Duplicado", source.value, "")
		for detail in person.inconsistencias:
			append_row(issues, person.referencia, "Inconsistencia", "", detail)

	warnings = book.create_sheet("Advertencias")
	append_row(warnings, "Advertencia")
	for warning in result.advertencias:
		append_row(warnings, warning)

	with BytesIO() as output:
		book.save(output)
		return output.getvalue()

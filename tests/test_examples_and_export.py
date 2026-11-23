import json
from io import BytesIO
from pathlib import Path
import pytest

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from conciliafecc.api import VALIDATIONS_PATH, create_app
from conciliafecc.contracts import Result, Source, Workbooks
from conciliafecc.export import export_result
from scripts.generar_excel_sinteticos import write_examples

EXAMPLES = Path(__file__).resolve().parents[1] / "docs" / "ejemplos"


def read_example(name):
	return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_http_examples(tmp_path):
	expected = read_example("validacion_exitosa.json")
	write_examples(tmp_path)
	uploads = {
		source.value: (f"{source.value}.xlsx", (tmp_path / f"{source.value}.xlsx").read_bytes())
		for source in Source
	}

	class StubEngine:
		def reconcile(self, workbooks: Workbooks) -> Result:
			for source in Source:
				content = getattr(workbooks, source.value)
				assert content == uploads[source.value][1]
				book = load_workbook(BytesIO(content), read_only=True)
				try:
					rows = list(book.active.values)
					assert rows[0] == ("clave_de_prueba", "marca_de_prueba")
					assert len(rows) - 1 == expected["registros_por_fuente"][source.value]
				finally:
					book.close()
			return Result.model_validate(expected)

	with TestClient(create_app(engine=StubEngine())) as client:
		response = client.post(VALIDATIONS_PATH, files=uploads)
		assert response.status_code == 200
		assert response.json() == expected

		uploads["biblioteca"] = ("corrupto.xlsx", b"datos de prueba")
		response = client.post(VALIDATIONS_PATH, files=uploads)
		assert response.status_code == 422
		assert response.json() == read_example("xlsx_invalido.json")


def test_export_preserves_rows_and_treats_user_strings_as_text():
	example = read_example("validacion_exitosa.json")
	example["personas"][0]["referencia"] = "=1+1"
	example["personas"][3]["inconsistencias"] = ["+prueba", "-prueba", "@prueba"]
	example["advertencias"] = ["#N/A"]
	book = load_workbook(BytesIO(export_result(Result.model_validate(example))), data_only=False)
	try:
		assert book["Resumen"]["B2"].value == 4
		assert book["Resumen"]["B5"].value == 1
		assert book["Personas"]["B2"].value is True
		assert list(book["Discrepancias"].values)[1:4] == [
			("P002", "Faltante", "biblioteca", None),
			("P002", "Faltante", "no_adeudos", None),
			("P003", "Duplicado", "biblioteca", None),
		]
		cells = [book["Personas"]["A2"], *book["Discrepancias"]["D"][4:], book["Advertencias"]["A2"]]
		assert [cell.value for cell in cells] == ["=1+1", "+prueba", "-prueba", "@prueba", "#N/A"]
		assert all(cell.data_type == "s" for cell in cells)
	finally:
		book.close()


def test_export_rejects_text_that_would_be_truncated():
	example = read_example("validacion_exitosa.json")
	example["advertencias"] = ["x" * 32768]
	with pytest.raises(ValueError, match="límite de una celda"):
		export_result(Result.model_validate(example))

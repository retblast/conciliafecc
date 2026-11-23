import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from conciliafecc.api import VALIDATIONS_PATH, Limits, create_app
from conciliafecc.contracts import EngineInputError, Result, Source, Workbooks


@pytest.fixture
def workbook():
	buffer = BytesIO()
	book = Workbook()
	book.active.append(["valor sintético"])
	book.close()
	book.save(buffer)
	return buffer.getvalue()


@pytest.fixture
def files(workbook):
	return {source.value: ("prueba.xlsx", workbook) for source in Source}


def test_health_and_unavailable_engine(files):
	with TestClient(create_app()) as client:
		assert client.get("/health").json() == {"estado": "ok", "motor": "pendiente"}
		response = client.post(VALIDATIONS_PATH, files=files)
	assert response.status_code == 503
	assert response.json()["error"]["codigo"] == "motor_no_disponible"
	assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("case", "status", "code"), [
	("missing", 422, "archivos_requeridos"),
	("duplicate", 422, "partes_invalidas"),
	("unknown", 422, "partes_invalidas"),
	("extension", 415, "tipo_no_admitido"),
	("empty", 422, "archivo_vacio"),
	("invalid", 422, "xlsx_invalido"),
	("file_limit", 413, "archivo_grande"),
	("expanded_limit", 413, "xlsx_grande"),
])
def test_upload_errors(files, workbook, case, status, code):
	limits = Limits()
	match case:
		case "missing":
			del files["ura"]
		case "duplicate":
			files = [*files.items(), ("ura", files["ura"])]
		case "unknown":
			files["extra"] = files["ura"]
		case "extension":
			files["ura"] = ("datos.xls", workbook)
		case "empty":
			files["ura"] = ("datos.xlsx", b"")
		case "invalid":
			files["ura"] = ("datos.xlsx", b"not an Excel file")
		case "file_limit":
			limits = Limits(file=len(workbook) - 1)
		case "expanded_limit":
			limits = Limits(expanded=128)
	with TestClient(create_app(limits=limits)) as client:
		response = client.post(VALIDATIONS_PATH, files=files)
	assert response.status_code == status
	assert response.json()["error"]["codigo"] == code


def test_rejects_corrupt_sheet(files, workbook):
	buffer = BytesIO()
	with ZipFile(BytesIO(workbook)) as source, ZipFile(buffer, "w") as target:
		for name in source.namelist():
			target.writestr(name, b"<unclosed>" if name == "xl/worksheets/sheet1.xml" else source.read(name))
	files["ura"] = ("datos.xlsx", buffer.getvalue())
	with TestClient(create_app()) as client:
		response = client.post(VALIDATIONS_PATH, files=files)
	assert response.status_code == 422
	assert response.json()["error"]["fuente"] == "ura"


def test_request_limits_apply_to_streams():
	with TestClient(create_app(limits=Limits(request=32))) as client:
		response = client.post(
			VALIDATIONS_PATH, content=iter([b"a" * 20, b"b" * 20]),
			headers={"Content-Type": "multipart/form-data; boundary=test"},
		)
	assert response.status_code == 413
	assert response.json()["error"]["codigo"] == "solicitud_grande"


def test_content_type_and_multipart_errors():
	with TestClient(create_app()) as client:
		assert client.post(VALIDATIONS_PATH, json={}).status_code == 415
		response = client.post(
			VALIDATIONS_PATH, content=b"invalid", headers={"Content-Type": "multipart/form-data"}
		)
	assert response.status_code == 400
	assert response.json()["error"]["codigo"] == "multipart_invalido"


@pytest.mark.parametrize(("outcome", "status"), [
	("ok", 200), ("input", 422), ("unexpected", 500), ("ambiguous", 500),
])
def test_engine_boundary(files, workbook, outcome, status):
	files["biblioteca"] = ("biblioteca.xlsx", workbook + b"lib")
	files["no_adeudos"] = ("no_adeudos.xlsx", workbook + b"clearance")

	class StubEngine:
		def reconcile(self, workbooks: Workbooks) -> Result:
			assert workbooks == Workbooks(workbook, workbook + b"lib", workbook + b"clearance")
			if outcome == "input":
				raise EngineInputError(Source.LIBRARY)
			if outcome == "unexpected":
				raise RuntimeError("información privada")
			return Result(
				registros_por_fuente={"ura": 1, "biblioteca": 0, "no_adeudos": 1},
				aprobados=int(outcome == "ambiguous"),
				faltantes_por_fuente={"ura": 0, "biblioteca": 1, "no_adeudos": 0},
				personas=[{
					"referencia": "caso-sintetico", "aprobada": outcome == "ambiguous",
					"faltantes": ["biblioteca"], "duplicados": [], "inconsistencias": [],
				}],
				advertencias=[],
			)

	with TestClient(create_app(engine=StubEngine())) as client:
		response = client.post(VALIDATIONS_PATH, files=files)
	assert response.status_code == status
	assert "información privada" not in response.text
	if outcome == "ok":
		assert response.json()["personas"][0]["faltantes"] == ["biblioteca"]
		assert response.json()["aprobados"] == 0
	elif outcome == "input":
		assert response.json()["error"]["fuente"] == "biblioteca"


def test_openapi_contract():
	with TestClient(create_app()) as client:
		spec = client.get("/openapi.json").json()
	operation = spec["paths"][VALIDATIONS_PATH]["post"]
	assert set(operation["responses"]) == {"200", "400", "413", "415", "422", "500", "503"}
	schema = operation["requestBody"]["content"]["multipart/form-data"]["schema"]["$ref"]
	assert set(spec["components"]["schemas"][schema.rsplit("/", 1)[-1]]["required"]) == {
		"ura", "biblioteca", "no_adeudos",
	}


def test_openapi_snapshot():
	snapshot = Path(__file__).resolve().parents[1] / "docs" / "openapi_spec.json"
	assert json.loads(snapshot.read_text(encoding="utf-8")) == create_app().openapi()


def test_method_not_allowed_preserves_allowed_methods():
	with TestClient(create_app()) as client:
		response = client.get(VALIDATIONS_PATH)
	assert response.status_code == 405
	assert response.headers["allow"] == "POST"

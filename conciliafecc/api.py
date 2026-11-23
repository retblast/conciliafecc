import os
from dataclasses import dataclass
from typing import Annotated

from fastapi import FastAPI, File, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Receive, Scope, Send

from .contracts import Engine, EngineInputError, ErrorDetail, ErrorResponse, Result, Source, Workbooks
from .uploads import UploadError, read_upload, validate_workbook

VALIDATIONS_PATH = "/api/v1/validaciones"


@dataclass(frozen=True)
class Limits:
	file: int = 5 * 1024**2
	request: int = 16 * 1024**2
	expanded: int = 32 * 1024**2

	def __post_init__(self) -> None:
		if min(self.file, self.request, self.expanded) <= 0:
			raise ValueError("Los límites deben ser positivos.")

	@classmethod
	def from_env(cls) -> "Limits":
		defaults = cls()
		return cls(
			file=int(os.getenv("CONCILIAFECC_MAX_FILE_BYTES", defaults.file)),
			request=int(os.getenv("CONCILIAFECC_MAX_REQUEST_BYTES", defaults.request)),
			expanded=int(os.getenv("CONCILIAFECC_MAX_EXPANDED_BYTES", defaults.expanded)),
		)


def error_response(
	status: int,
	code: str,
	message: str,
	source: Source | None = None,
	*,
	headers: dict[str, str] | None = None,
) -> JSONResponse:
	body = ErrorResponse(error=ErrorDetail(codigo=code, mensaje=message, fuente=source))
	return JSONResponse(
		body.model_dump(mode="json"), status_code=status,
		headers={**(headers or {}), "Cache-Control": "no-store"},
	)


class UploadBodyLimit:
	def __init__(self, app: ASGIApp, limit: int):
		self.app = app
		self.limit = limit

	async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
		if scope["type"] != "http" or scope["method"] != "POST" or (
			scope["path"].rstrip("/") != VALIDATIONS_PATH
		):
			await self.app(scope, receive, send)
			return

		request = Request(scope)
		media_type = request.headers.get("content-type", "").partition(";")[0].strip().lower()
		if media_type != "multipart/form-data":
			response = error_response(415, "tipo_solicitud", "Se requiere multipart/form-data.")
			await response(scope, receive, send)
			return

		body = bytearray()
		while True:
			message = await receive()
			if message["type"] == "http.disconnect":
				return
			chunk = message.get("body", b"")
			if len(body) + len(chunk) > self.limit:
				response = error_response(413, "solicitud_grande", "La solicitud supera el límite.")
				await response(scope, receive, send)
				return
			body.extend(chunk)
			if not message.get("more_body", False):
				break

		async def replay():
			if body:
				chunk = bytes(body)
				body.clear()
				return {"type": "http.request", "body": chunk, "more_body": False}
			return {"type": "http.request", "body": b"", "more_body": False}

		await self.app(scope, replay, send)


def create_app(engine: Engine | None = None, limits: Limits | None = None) -> FastAPI:
	limits = limits if limits is not None else Limits.from_env()
	app = FastAPI(title="ConciliaFECC", version="0.1.0")
	app.add_middleware(UploadBodyLimit, limit=limits.request)

	@app.exception_handler(RequestValidationError)
	async def invalid_request(request: Request, error: RequestValidationError):
		if request.url.path != VALIDATIONS_PATH:
			return error_response(422, "solicitud_invalida", "La solicitud es inválida.")
		fields = {item["loc"][-1] for item in error.errors()}
		source = next((item for item in Source if item.value in fields), None)
		return error_response(422, "archivos_requeridos", "Se requieren tres archivos.", source)

	@app.exception_handler(HTTPException)
	async def http_error(request: Request, error: HTTPException):
		if request.url.path == VALIDATIONS_PATH and error.status_code == 400:
			return error_response(400, "multipart_invalido", "La carga multipart es inválida.")
		return error_response(
			error.status_code, "error_http", "La solicitud no se pudo atender.",
			headers=error.headers,
		)

	@app.get("/health")
	def health() -> dict[str, str]:
		return {"estado": "ok", "motor": "configurado" if engine is not None else "pendiente"}

	@app.post(
		VALIDATIONS_PATH,
		response_model=Result,
		responses={
			400: {"model": ErrorResponse, "description": "Carga multipart inválida."},
			413: {"model": ErrorResponse, "description": "Límite excedido."},
			415: {"model": ErrorResponse, "description": "Formato no admitido."},
			422: {"model": ErrorResponse, "description": "Archivos o datos inválidos."},
			500: {"model": ErrorResponse, "description": "Error del motor."},
			503: {"model": ErrorResponse, "description": "Motor no disponible."},
		},
	)
	async def validate(
		request: Request,
		response: Response,
		ura: Annotated[UploadFile, File(description="Excel de URA.")],
		biblioteca: Annotated[UploadFile, File(description="Excel de Biblioteca.")],
		no_adeudos: Annotated[UploadFile, File(description="Excel de Constancia de No Adeudos.")],
	) -> Result | JSONResponse:
		form = await request.form()
		if sorted(form.keys()) != sorted(source.value for source in Source) or len(form.multi_items()) != 3:
			return error_response(422, "partes_invalidas", "Envía un archivo por fuente.")

		try:
			contents = {}
			for source, upload in zip(Source, (ura, biblioteca, no_adeudos), strict=True):
				content = await read_upload(upload, source, limits.file)
				await run_in_threadpool(validate_workbook, content, source, limits.expanded)
				contents[source.value] = content
		except UploadError as error:
			return error_response(error.status, error.code, error.message, error.source)

		if engine is None:
			return error_response(503, "motor_no_disponible", "El motor no está disponible.")
		try:
			result = await run_in_threadpool(engine.reconcile, Workbooks(**contents))
			validated = Result.model_validate(result.model_dump())
			response.headers["Cache-Control"] = "no-store"
			return validated
		except EngineInputError as error:
			return error_response(422, "datos_invalidos", "El motor rechazó los datos de la fuente.", error.source)
		except Exception:
			return error_response(500, "error_motor", "No se pudo completar la conciliación.")

	return app


app = create_app()

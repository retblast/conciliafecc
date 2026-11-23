from io import BytesIO
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile
from zlib import error as CompressionError

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import iterparse
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from starlette.datastructures import UploadFile

from .contracts import Source


class UploadError(Exception):
	def __init__(self, status: int, code: str, message: str, source: Source):
		self.status = status
		self.code = code
		self.message = message
		self.source = source


async def read_upload(upload: UploadFile, source: Source, limit: int) -> bytes:
	if not (upload.filename or "").lower().endswith(".xlsx"):
		raise UploadError(415, "tipo_no_admitido", "Se requiere un archivo .xlsx.", source)
	content = await upload.read(limit + 1)
	if len(content) > limit:
		raise UploadError(413, "archivo_grande", "El archivo supera el límite.", source)
	if not content:
		raise UploadError(422, "archivo_vacio", "El archivo está vacío.", source)
	return content


def validate_workbook(content: bytes, source: Source, expanded_limit: int) -> None:
	try:
		with ZipFile(BytesIO(content)) as archive:
			members = archive.infolist()
			if len(members) > 2048 or sum(item.file_size for item in members) > expanded_limit:
				raise UploadError(413, "xlsx_grande", "El contenido del Excel supera el límite.", source)
			if len({item.filename for item in members}) != len(members):
				raise ValueError("Entradas ZIP duplicadas.")
			for item in members:
				with archive.open(item) as stream:
					if item.filename.lower().endswith((".xml", ".rels")):
						stack = []
						for event, node in iterparse(
							stream, events=("start", "end"), forbid_dtd=True
						):
							if event == "start":
								stack.append(node)
							else:
								stack.pop()
								if stack:
									stack[-1].remove(node)
					else:
						while stream.read(65536):
							pass
		workbook = load_workbook(BytesIO(content), read_only=True, keep_links=False)
		try:
			if not workbook.worksheets:
				raise ValueError("No hay hojas de cálculo.")
		finally:
			workbook.close()
	except (BadZipFile, InvalidFileException, ParseError, DefusedXmlException, KeyError,
			ValueError, TypeError, RuntimeError, NotImplementedError, OSError, EOFError,
			IndexError, OverflowError, AttributeError, CompressionError) as error:
		raise UploadError(422, "xlsx_invalido", "El archivo Excel es inválido.", source) from error

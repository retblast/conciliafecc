from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator


class Source(StrEnum):
	URA = "ura"
	LIBRARY = "biblioteca"
	CLEARANCE = "no_adeudos"


@dataclass(frozen=True)
class Workbooks:
	ura: bytes
	biblioteca: bytes
	no_adeudos: bytes


class SourceCounts(BaseModel):
	ura: int = Field(ge=0)
	biblioteca: int = Field(ge=0)
	no_adeudos: int = Field(ge=0)


class PersonResult(BaseModel):
	referencia: str = Field(min_length=1)
	aprobada: bool
	faltantes: list[Source]
	duplicados: list[Source]
	inconsistencias: list[str]

	@model_validator(mode="after")
	def check_approval(self) -> "PersonResult":
		if self.aprobada and (self.faltantes or self.duplicados or self.inconsistencias):
			raise ValueError("Un registro con discrepancias no puede aprobarse.")
		return self


class Result(BaseModel):
	registros_por_fuente: SourceCounts
	aprobados: int = Field(ge=0)
	faltantes_por_fuente: SourceCounts
	personas: list[PersonResult]
	advertencias: list[str]

	@model_validator(mode="after")
	def check_counts(self) -> "Result":
		if self.aprobados != sum(person.aprobada for person in self.personas):
			raise ValueError("Total de aprobados incoherente.")
		for source in Source:
			count = sum(source in person.faltantes for person in self.personas)
			if getattr(self.faltantes_por_fuente, source.value) != count:
				raise ValueError("Total de faltantes incoherente.")
		return self


class ErrorDetail(BaseModel):
	codigo: str
	mensaje: str
	fuente: Source | None = None


class ErrorResponse(BaseModel):
	error: ErrorDetail


class EngineInputError(Exception):
	"""El motor rechaza los datos de una fuente."""

	def __init__(self, source: Source):
		self.source = source


class Engine(Protocol):
	def reconcile(self, workbooks: Workbooks) -> Result: ...

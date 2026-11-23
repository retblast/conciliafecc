import argparse
from pathlib import Path

from openpyxl import Workbook

ROWS = {
	"ura": [("P001", "A"), ("P002", "B"), ("P003", "C"), ("P004", "D")],
	"biblioteca": [("P001", "A"), ("P003", "C"), ("P003", "C"), ("P004", "X")],
	"no_adeudos": [("P001", "A"), ("P003", "C"), ("P004", "D")],
}


def write_examples(directory: Path) -> None:
	directory.mkdir(parents=True, exist_ok=True)
	for source, rows in ROWS.items():
		workbook = Workbook()
		sheet = workbook.active
		sheet.title = "Datos sintéticos"
		sheet.append(["clave_de_prueba", "marca_de_prueba"])
		for row in rows:
			sheet.append(row)
		with (directory / f"{source}.xlsx").open("xb") as output:
			workbook.save(output)


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Genera tres Excel de prueba.")
	parser.add_argument("directorio", type=Path)
	write_examples(parser.parse_args().directorio)

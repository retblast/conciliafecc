# Semana 13 · Motor de conciliación — Iván Sánchez Silva

**Fecha:** 2026-11-25  
**Responsable:** Iván Sánchez Silva (integrante 3 — motor de procesamiento)  
**Repositorio:** `https://github.com/retblast/conciliafecc`  
**Rama:** `feat/motor-conciliacion-inicial`  
**Base:** PR #1 mergeado en `main`

---

## 1. Objetivos de la semana

1. Revisar el estado real del repositorio y el contrato propuesto por retblast.
2. Confirmar que `Engine.reconcile(Workbooks) -> Result` sirve para el motor.
3. Inspeccionar estructuralmente los cuatro Excel institucionales recibidos.
4. Hacer preguntas con opciones y recomendaciones para fijar el diseño.
5. Producir un documento de diseño detallado, con diagramas y criterios de
   aceptación, antes de consolidar código.
6. Dejar todo preparado para revisión **sin commitear ni pushear** sin permiso.

---

## 2. Actividades realizadas

### 2026-11-25 — Inspección del repositorio

Se revisaron `README.md`, `AGENTS.md`, `pyproject.toml`, `flake.nix`, el CI,
`docs/CONTRATO_API.md`, `docs/openapi_spec.json`, la bitácora de retblast,
`api.py`, `uploads.py`, `contracts.py`, `export.py` y las 22 pruebas existentes.

Estado encontrado: backend con carga y validación de XLSX, DTOs e interfaz
`Engine`, exportador provisional y sin motor conectado. El endpoint responde
`503` con archivos válidos hasta inyectar una implementación. No se modificó
ningún archivo de retblast ni de Renzo.

### 2026-11-25 — Borrador sintético inicial (histórico)

Se crearon localmente, **sin commit**, `conciliafecc/motor.py`,
`tests/test_motor.py`, `docs/MOTOR_CONCILIACION.md` y esta bitácora. El borrador
usaba una regla conservadora: sin estados explícitos en las tres fuentes,
`aprobados = 0`. Pasaba 30 pruebas con datos sintéticos y `ruff` limpio.

> **Este borrador queda superado por el diseño de abajo.** Se conserva como
> evidencia del primer acercamiento, no como implementación final.

### 2026-11-25 — Recepción e inspección de los Excel reales

Los cuatro archivos están en `C:\Users\Alfredo\Downloads`
(`/mnt/c/Users/Alfredo/Downloads`):

- `REPOSITORIO_BACH_LICENC_APTOS COLACION 18-SET_2026 -11AGTO.xlsx`
- `BACHILLERES O LICENCIADOS APTOS COLACION 18-SETIEMBRE 2026 (1).xlsx`
- `Libro2.xlsx`
- `COLACION ORD_FACEDU_18-SET-2026_NUEVO FORMATO.xlsx` (lista final)

La inspección fue **solo estructural**: hojas, filas, columnas, cabeceras,
tipos de celda, conteos y solapamientos agregados. No se copió ningún archivo al
repo, no se volcaron filas ni datos personales a logs y no se versionaron
resultados nominales.

Hallazgos agregados:

| Dato | Valor |
|---|---:|
| Matrículas en cada archivo de 63 | 63 y 63, idénticas entre sí |
| Matrículas en `Libro2.xlsx` | 47 |
| Intersección de las tres entradas | 31 |
| Unión de las tres entradas | 79 |
| Matrículas en la unión de hojas de la final | 95 |
| Aprobados por la regla ratificada vs. final | 18 de 31 coinciden |

### 2026-11-25 — Rondas de preguntas y decisiones

Se hicieron dos rondas de preguntas con opciones y recomendación explícita,
como se hizo en VistoBueno. El encargado ratificó todas las recomendaciones:

| Decisión | Resultado |
|---|---|
| Mapa de fuentes | `BACHILLERES...` = URA; `REPOSITORIO...` = Biblioteca; `Libro2` = No Adeudos |
| Clave de persona | Matrícula normalizada; DNI solo referencia secundaria |
| Aprobación del MVP | Presencia en las tres, sin duplicados ni inconsistencias |
| Lista final | Verdad de prueba, no cuarta entrada HTTP |
| Hojas | `Worksheet` y `Hoja1`; se ignoran `TITULACION SEP 2026...` |
| Duplicados | Se marcan y bloquean la aprobación |
| Comparación con la final | Cobertura y precisión, no igualdad estricta |
| Descarga | POST binario con tres archivos; el motor sigue devolviendo `Result` |

Quedó registrado que la regla de aprobación es un **supuesto ratificado para el
MVP** y que todavía requiere confirmación institucional antes de presentarla
como requisito de las dependencias.

### 2026-11-25 — Diseño detallado

Se reemplazó `docs/MOTOR_CONCILIACION.md` por un diseño completo con:

- Diagrama de contexto, flujo interno, secuencia con la API y clasificación de
  una persona (Mermaid).
- Tabla de evidencia estructural de los cuatro Excel, sin PII.
- Registro de las preguntas respondidas y sus consecuencias.
- Modelo de datos interno y mapeo a los DTOs del contrato.
- Configuración de lectura por `Source`.
- Reglas RN-01 a RN-10, errores, privacidad y complejidad.
- Plan de pruebas sintéticas y regresión agregada contra la final.
- Criterios de aceptación, riesgos, dependencias y plan de commits.

### 2026-11-25 — Implementación y verificación

Tras la autorización del encargado se reescribió `conciliafecc/motor.py` según
el diseño y se amplió `tests/test_motor.py` a 11 casos sintéticos. El motor:

- lee `Worksheet` con cabecera en fila 2 y `Hoja1` sin cabecera;
- normaliza matrículas numéricas y textuales, preservando ceros a la izquierda;
- detecta duplicados, faltantes, filas sin matrícula, identificadores inválidos
  y discrepancias de nombres;
- aplica la presencia en tres como regla de aprobación y emite la advertencia
  del supuesto pendiente;
- devuelve referencias opacas `P0001…` y totales derivados desde `personas`.

Verificación local:

```sh
PYTHONPATH=/home/ivan/pylibs:/tmp/opencode/pylibs-conciliafecc \
  python3 -m pytest -q
```

Resultado: **33 pasadas** (22 previas + 11 nuevas). `ruff check
conciliafecc/motor.py tests/test_motor.py` quedó limpio.

Se ejecutó además una verificación agregada contra los tres Excel reales, sin
imprimir celdas ni identificadores: `ura 63 / biblioteca 63 / no_adeudos 47`,
`aprobados 31`, `faltantes ura 16 / biblioteca 16 / no_adeudos 32`, `79
personas`. Coincide con el diseño. No se guardó ningún resultado nominal.

---

## 3. Evidencias producidas

| Evidencia | Archivo / comando |
|---|---|
| Estado del repo y PR #1 | `gh pr view 1 --repo retblast/conciliafecc` y lectura de archivos |
| Inspección estructural | Script local `openpyxl` sin impresión de celdas (no versionado) |
| Diseño detallado | `docs/MOTOR_CONCILIACION.md` |
| Bitácora | `docs/semana13_trabajo_ivanSanchezSil.md` |
| Borrador sintético previo | `30 passed`; superado por la implementación final |
| Implementación final | `conciliafecc/motor.py` |
| Pruebas finales | `tests/test_motor.py`, 11 casos |
| Suite final | `33 passed`; `ruff` limpio |
| Verificación agregada real | Conteos reproducidos en §2; sin PII versionada |

---

## 4. Dificultades y aprendizajes

- El entorno local no tiene `nix` ni `uv`; se usó un `PYTHONPATH` alternativo.
  `defusedxml` se instaló solo en `/tmp/opencode/pylibs-conciliafecc`, fuera del
  repositorio.
- Los dos archivos de 63 filas son indistinguibles por contenido; el mapeo a
  URA/Biblioteca depende de la decisión ratificada y del campo `Workbooks`.
- La lista final es más grande que la unión de las entradas. Compararla por
  igualdad habría producido diferencias engañosas; por eso se definieron
  cobertura, precisión y tres grupos de discrepancias.
- Las matrículas con ceros a la izquierda aparecen como texto en dos archivos y
  coinciden entre sí; recortar los ceros no mejoró la coincidencia observada.

---

## 5. Estado de los cambios

La rama `feat/motor-conciliacion-inicial` contiene la implementación final, las
pruebas y la documentación. El encargado autorizó commits, push y PR; se
preparan commits atómicos y el PR para revisión. **No se mergea desde este
hilo.**

---

## 6. Plan siguiente

1. Commits atómicos: motor, pruebas y documentación.
2. Push de la rama y apertura del PR para revisión.
3. Coordinar con retblast la inyección del motor y el POST de descarga; con
   Renzo, la presentación de referencias opacas.
4. Pedir a las áreas la confirmación institucional del mapa y de la regla de
   aprobación antes de hablar de integración real.
5. Ampliar cobertura futura con las hojas `TITULACION SEP 2026...` solo si el
   equipo decide que aportan datos originales necesarios.

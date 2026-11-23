# Contrato preliminar del Backend/API

## Flujo

```mermaid
flowchart LR
    Frontend -->|Tres archivos XLSX| API[API HTTP]
    API -->|Workbooks con bytes por fuente| Motor[Motor de conciliación]
    Motor -->|Result o EngineInputError| API
    API -->|Resultado o error JSON| Frontend
```

El flujo se lee de izquierda a derecha. La API valida los archivos antes de invocar al motor.

## Operaciones

- `GET /health` devuelve `estado: ok` y el estado de configuración del `motor` (`pendiente` o `configurado`). Mide si el servicio responde.
- `POST /api/v1/validaciones` recibe exactamente tres partes de archivo en `multipart/form-data`: `ura`, `biblioteca` y `no_adeudos`. Devuelve un resultado JSON síncrono con estado 200 cuando el motor está conectado.

La API admite `.xlsx`. Comprueba el tamaño, el XML, la integridad del ZIP y que el libro tenga hojas de cálculo. La comprobación de columnas, tipos de celda y reglas de negocio pertenece al motor. La API limita el cuerpo antes de analizar el formulario y cierra las cargas temporales al terminar la solicitud.

| Variable | Límite inicial |
|---|---:|
| `CONCILIAFECC_MAX_FILE_BYTES` | 5 MiB por archivo |
| `CONCILIAFECC_MAX_REQUEST_BYTES` | 16 MiB por solicitud |
| `CONCILIAFECC_MAX_EXPANDED_BYTES` | 32 MiB por ZIP expandido |

Los valores de entorno se expresan en bytes. Cada ZIP admite hasta 2048 entradas. El límite del cuerpo se aplica también sin `Content-Length`.

## Resultado

| Campo | Significado |
|---|---|
| `registros_por_fuente` | Total de registros por cada una de las tres fuentes según el motor. |
| `aprobados` | Total de personas aprobadas. |
| `faltantes_por_fuente` | Personas ausentes por fuente. Una persona puede contar en varias fuentes. |
| `personas` | Resultados individuales con `referencia`, `aprobada`, `faltantes`, `duplicados` e `inconsistencias`. |
| `advertencias` | Avisos generales aptos para mostrar en el frontend. |

Usa una referencia opaca dentro del resultado. Las listas `faltantes` y `duplicados` contienen nombres de fuentes. `inconsistencias` contiene descripciones sin datos personales. El contrato rechaza aprobaciones con discrepancias registradas y comprueba los totales derivados de `personas`.

## Errores

El cuerpo sigue el formato `{"error":{"codigo":"…","mensaje":"…","fuente":null}}`. Si se puede atribuir el error a una fuente, `fuente` contiene su nombre.

| HTTP | Casos |
|---|---|
| 400 | Carga multipart mal formada. |
| 413 | Cuerpo, archivo o ZIP expandido supera el límite. |
| 415 | Tipo de solicitud o extensión incompatible. |
| 422 | Archivo vacío, corrupto, faltante, parte extra o repetida, o datos rechazados por el motor. |
| 500 | Error inesperado del motor o resultado que incumple el contrato. |
| 503 | Archivos válidos con el motor pendiente de integración. |

Los errores omiten el contenido de las celdas, los nombres de archivos y los detalles de excepciones.

## Interfaz con el motor

`Engine.reconcile(workbooks: Workbooks) -> Result` recibe los bytes originales de las tres fuentes en atributos separados. Se ejecuta de forma síncrona en un hilo de trabajo. Puede lanzar `EngineInputError(source)` al rechazar los datos de una fuente. `create_app(engine=...)` conecta una implementación. Las pruebas inyectan un simulador.

## Descarga y decisiones pendientes

El POST actual entrega el resultado directamente y evita guardar resultados o asignar IDs. Los GET por ID requieren acordar almacenamiento, acceso, vigencia y eliminación. Para mantener el MVP síncrono, se propone acordar un modo de descarga binaria del POST que reciba los tres archivos y ejecute la conciliación de nuevo. Renzo e Iván deben validar ese flujo antes de fijar el contrato de descarga.

Confirma con las áreas las hojas, columnas, tipos de datos, identificador de persona, normalización, duplicados, estados de aprobación y formato de salida. La presencia en las tres fuentes solo podrá servir como regla provisional si estas carecen de estados de aprobación y los casos ambiguos quedan fuera. Para la exportación, prueba que los valores que parezcan fórmulas permanezcan como texto.

## Ejemplos para integrar

Genera tres archivos sintéticos en un directorio nuevo.

```sh
nix develop path:. -c uv run --locked python scripts/generar_excel_sinteticos.py muestras-sinteticas
```

- [Respuesta 200](ejemplos/validacion_exitosa.json). Incluye un aprobado, una persona ausente de dos fuentes, un duplicado y una coincidencia ambigua. El resultado está escrito a mano y el simulador lo devuelve en la prueba HTTP.
- [Respuesta 422](ejemplos/xlsx_invalido.json). La API genera este error cuando falla la validación del archivo de Biblioteca.

Las columnas `clave_de_prueba` y `marca_de_prueba` solo sirven para comprobar la entrega de archivos entre componentes. El caso aprobado y la ambigüedad son valores del ejemplo. El motor real deberá determinar esas condiciones con las reglas acordadas.

El exportador provisional `export_result(Result) -> bytes` genera las hojas Resumen, Personas, Discrepancias y Advertencias. La prueba vuelve a abrir el Excel generado y comprueba los faltantes y los tipos de celda. El exportador aún funciona como una función interna. Falta acordar el flujo HTTP de descarga y el formato institucional.

# Semana 13 · Backend/API de ConciliaFECC

El plan actualizado asigna las actividades 9–14 a ConciliaFECC. Las actividades 1–8 corresponden a VistoBueno.

El repositorio inicial tenía una rama `main` y un commit con la licencia MIT. La revisión de VistoBueno incluyó su guía, el contrato HTTP, el código de la API, los modelos y la suite de pruebas de contrato. De esa referencia se adoptaron la separación entre API y motor, los modelos explícitos, las pruebas de contrato y la bitácora semanal.

| Actividad | Estado | Evidencia |
|---|---|---|
| 9 · Requisitos y frontera | Análisis documentado. Muestras reales pendientes. | Contrato y diagrama de integración. |
| 10 · Contrato y DTOs | Diseño preliminar. Descarga propuesta. | `docs/CONTRATO_API.md`, `docs/openapi_spec.json`, `conciliafecc/contracts.py`. |
| 11 · Carga y errores | Implementada con pruebas sintéticas. | `conciliafecc/api.py`, `conciliafecc/uploads.py`, `tests/test_api_contract.py`. |
| 12 · Motor y Excel | Interfaz probada con simulador. Integración real y descarga pendientes. | `Engine`, `Workbooks` y pruebas de la frontera con el motor. |
| 13 · Pruebas de contrato e integración | Pruebas sintéticas de HTTP y del adaptador. Integración real pendiente. | `tests/test_api_contract.py`. |
| 14 · Documentación | Contrato preliminar y decisiones pendientes registrados. | Contrato y especificación OpenAPI. |

El diseño de interfaces aplica Ingeniería de Software I. La validación, el manejo de errores y las pruebas aplican Ingeniería de Software II.

## Verificación

- `nix develop path:. -c uv run --locked pytest -q` ejecutó 18 pruebas. Todas pasaron. La suite comprueba que la especificación OpenAPI guardada coincida con la que genera la API.
- Una instancia local de Uvicorn respondió 200 a `GET /health`. El estado del motor fue `pendiente`.

## Evidencias adicionales con datos sintéticos

- Actividades 10 y 13. Los ejemplos JSON se comprobaron contra respuestas HTTP. La prueba genera los tres Excel y verifica los archivos que recibe el simulador.
- Actividad 12. El exportador provisional se verificó con el resultado sintético. Sigue pendiente la integración real, el formato institucional y la descarga HTTP.

## Revisión previa al PR

La revisión comprobó que la API conserva la cabecera `Allow` en respuestas 405. El exportador rechaza el texto que supera el límite de una celda. Las pruebas de ambos casos se ejecutan con la suite de Nix.

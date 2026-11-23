# ConciliaFECC

API para conciliar los listados de URA, Biblioteca y Constancia de No Adeudos de la Facultad de Educación y Ciencias de la Comunicación de la Universidad Nacional de Trujillo.

El primer incremento recibe y valida tres archivos `.xlsx`. La conciliación y la descarga del Excel consolidado requieren la integración con el motor.

## Desarrollo

Usa Nix con flakes habilitados. Nix selecciona Python y uv. uv instala las dependencias de `uv.lock` en un entorno local.

```sh
nix develop -c uv run --locked uvicorn conciliafecc.api:app --host 127.0.0.1
nix develop -c uv run --locked pytest -q
```

Si los archivos de la flake siguen sin registrar en Git, usa `nix develop path:.` para incluirlos.

Consulta `/health` para ver el estado del servicio, `/docs` para probar la API y `/openapi.json` para descargar la especificación. El [contrato](docs/CONTRATO_API.md) describe las solicitudes, los resultados y la interfaz con el motor.

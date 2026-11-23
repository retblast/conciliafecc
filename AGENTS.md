# Guía de trabajo de ConciliaFECC

## Alcance y responsables

- retblast mantiene Backend/API, contratos, carga de archivos, entrega de resultados y pruebas HTTP.
- Renzo mantiene Frontend/UI.
- Iván mantiene el motor de conciliación.
- Coordina con el responsable antes de editar su componente. Acuerda con ambos responsables los cambios que afecten sus interfaces.

## Estructura

- `conciliafecc/api.py` define las rutas HTTP y adapta los errores a respuestas.
- `conciliafecc/uploads.py` comprueba la carga y la estructura de los Excel.
- `conciliafecc/contracts.py` define los modelos de datos y la interfaz del motor.
- `tests/` contiene pruebas automatizadas que generan archivos sintéticos.
- `docs/CONTRATO_API.md` documenta las interfaces y decisiones pendientes.
- `docs/semana{N}_trabajo_{usuario}.md` registra las actividades y sus evidencias.

El motor puede importar el contrato compartido. La API recibe una implementación de la interfaz. Mantén separados el transporte HTTP y las reglas de conciliación.

## Flujo de cambios

- Propón el plan y revisa el alcance antes de implementar. Usa una rama por tarea y un PR pequeño para revisar los cambios.
- Agrupa cada cambio lógico con sus pruebas en un commit atómico. Usa mensajes breves en español, como `feat(api): validar la carga de tres Excel`.
- Solicita autorización para crear commits, publicar ramas o abrir PRs. Mantén los cambios de otros integrantes fuera de tu diff.
- Ejecuta `nix develop -c uv run --locked pytest -q`. Actualiza el contrato y OpenAPI cuando cambie la interfaz. Añade pruebas para cada comportamiento nuevo.
- En la bitácora, distingue diseño, verificación con datos sintéticos e integración real. Incluye los archivos y comandos que permiten reproducir cada evidencia.

## Datos y seguridad

Usa muestras sintéticas para el desarrollo y las pruebas. Mantén los Excel institucionales, sus resultados y los datos personales fuera del repositorio y de los logs. Coordina el formato y las reglas cuando lleguen las muestras autorizadas. Los casos ambiguos requieren revisión. En la exportación, escribe los valores de texto como celdas de texto y prueba que Excel no los interprete como fórmulas.

# Semana 14 · Frontend/UI de ConciliaFECC

- **Integrante**: Renzo (Integrante 2 — Frontend / React)
- **Semana**: 14
- **Fechas**: 2026-11-25 → 2026-11-25
- **Rol**: Frontend (React + Vite): interfaz de carga, integración con la API,
  visualización de resultados y descarga.
- **Rama**: `semana14-frontend-conciliafecc` (desde `main`)
- **Repositorio**: fork `Rodo00/conciliafecc` de `retblast/conciliafecc`

---

## Contexto

El backend de ConciliaFECC ya está implementado (actividades 9–14 por retblast):
`POST /api/v1/validaciones` recibe tres archivos `.xlsx` (`ura`, `biblioteca`,
`no_adeudos`) y devuelve el resultado de conciliación. El motor aún no está
integrado (estado `pendiente` en `GET /health`), por lo que el frontend debe
funcionar con respuestas simuladas hasta que Iván entregue el motor real.

El frontend no existía previamente en el repositorio; se creó desde cero.

---

## Actividades realizadas (NUEVO_PROYECTO.txt, integrante 2)

### Actividad 1 — Analizar requisitos de interacción para carga de los 3 archivos Excel

**Producto**: Requisitos y flujo de interfaz.

Requisitos identificados:
- Tres inputs de archivo, uno por fuente: `ura` (URA), `biblioteca` (Biblioteca),
  `no_adeudos` (Constancia de No Adeudos).
- Cada archivo debe ser `.xlsx`, ≤5 MiB por archivo, ≤16 MiB total por request
  (límites del backend en `conciliafecc/api.py`).
- Botón «Conciliar» deshabilitado hasta que los 3 archivos estén seleccionados.
- POST multipart/form-data a `/api/v1/validaciones`.
- Estado de carga durante el procesamiento; botón deshabilitado para evitar
  peticiones duplicadas.
- Éxito: resumen (registros por fuente, aprobados, faltantes por fuente) +
  tabla de personas con referencia, aprobada, faltantes, duplicados,
  inconsistencias.
- Error: mensaje comprensible con código de error y fuente si aplica.
- Descarga de resultados (CSV inmediato; Excel pendiente de contrato HTTP con
  Iván/retblast).

### Actividad 2 — Diseñar la interfaz de carga de archivos URA, Biblioteca y No Adeudos

**Producto**: `frontend/src/components/UploadForm.jsx`.

- Tres campos de archivo etiquetados con el nombre de cada dependencia.
- Cada input acepta solo `.xlsx` (`accept=".xlsx"`).
- Muestra nombre y tamaño (KB) del archivo seleccionado.
- Botón «Conciliar archivos» deshabilitado si falta algún archivo o si hay una
  conciliación en curso.
- Aviso de error integrado cuando la API devuelve un fallo.

### Actividad 3 — Implementar la comunicación con la API de conciliación

**Producto**: `frontend/src/api/client.js`.

- `conciliar(archivos)`: envía los tres archivos como `multipart/form-data` a
  `${API_BASE}/api/v1/validaciones`.
- `healthCheck()`: consulta `GET /health` para verificar el estado del servicio.
- `ConciliationApiError`: lanza error con `status`, `codigo`, `mensaje` y
  `fuente` cuando la API responde con error (400, 413, 415, 422, 500, 503).
- `SOURCES` y `sourceLabel()`: constantes para las tres fuentes y sus etiquetas
  legibles.
- `API_BASE` configurable vía `VITE_API_URL`; por defecto `/api` (proxy de Vite
  hacia `http://127.0.0.1:8000`).

### Actividad 4 — Desarrollar la visualización de personas aprobadas y faltantes por lista

**Producto**: `frontend/src/components/ResultsTable.jsx` (`ResultSummary` +
`ResultsTable` + `PersonRow`).

- `ResultSummary`: tabla con registros y faltantes por fuente, total de
  aprobados y lista de advertencias.
- `ResultsTable`: tabla de personas con columnas: Referencia, Aprobada,
  Faltantes, Duplicados, Inconsistencias.
- `PersonRow`: fila por persona; filas aprobadas con fondo verde, observadas con
  fondo ámbar; guión «—» cuando no hay faltantes/duplicados/inconsistencias.
- Contador de personas aprobadas y con observaciones.

### Actividad 5 — Implementar la descarga del archivo Excel consolidado y la presentación de errores

**Producto**: `frontend/src/App.jsx` (descarga CSV) +
`frontend/src/components/ErrorMessage.jsx` (errores).

- `ErrorMessage`: muestra el mensaje de error en un `div` con `role="alert"`.
- `manejarDescarga()` en `App`: genera un archivo CSV con todas las personas
  (referencia, aprobada, faltantes, duplicados, inconsistencias) y lo descarga
  como `conciliafecc_resultados.csv`.
- Botón «Descargar resultados (CSV)» visible después de una conciliación exitosa.
- Nota informativa: la descarga del Excel consolidado (.xlsx) está pendiente de
  coordinación del contrato HTTP con el backend
  (`docs/CONTRATO_API.md` §Descarga y decisiones pendientes).

### Actividad 6 — Ejecutar pruebas de interfaz, integración y usabilidad; documentar resultados

**Producto**: `frontend/src/tests/components.test.jsx` (17 tests).

Pruebas implementadas:
- `sourceLabel`: etiquetas legibles de las 3 fuentes.
- `UploadForm`: 3 inputs etiquetados, accept `.xlsx`, botón deshabilitado sin
  archivos, habilitado con 3 archivos, `onConciliar` con los 3 archivos, nombre
  y tamaño mostrados, botón deshabilitado durante carga, aviso de error.
- `ResultSummary`: registros/aprobados/faltantes por fuente, advertencias.
- `ResultsTable`: tabla de personas, guión cuando faltan datos, contador
  aprobadas/observadas.
- `ErrorMessage`: mensaje en `role="alert"`.
- `API client - conciliar`: envía multipart/form-data, devuelve resultado,
  lanza error con mensaje de la API en fallos.

Verificación:
- `npm test` → **17 passed** (1 archivo de tests).
- `npm run lint` → **0 errores** (ESLint con plugin react + react-hooks).
- `npm run build` → **148.29 kB** (Vite, producción).

---

## Decisiones que requieren coordinación

| Decisión | Con quién coordinar | Estado |
|----------|--------------------|--------|
| Contrato de descarga HTTP del Excel consolidado | Iván (motor) + retblast (API) | Pendiente — `docs/CONTRATO_API.md` §Descarga |
| Integración del motor real (reemplazar simulación) | Iván (motor) | Pendiente — motor en estado `pendiente` |
| Formato institucional de salida | Iván + áreas de la facultad | Pendiente — esperar Excel institucionales |

---

## Evidencias producidas

- `frontend/package.json` — dependencias y scripts (dev, build, lint, test).
- `frontend/vite.config.js` — Vite + React, proxy `/api` → `127.0.0.1:8000`,
  esbuild JSX automático.
- `frontend/index.html` — punto de entrada.
- `frontend/src/main.jsx` — render de React con import de CSS.
- `frontend/src/index.css` — estilos de la interfaz.
- `frontend/src/App.jsx` — estado de la aplicación, conciliación, descarga CSV.
- `frontend/src/api/client.js` — cliente de la API de conciliación.
- `frontend/src/components/UploadForm.jsx` — formulario de carga de 3 archivos.
- `frontend/src/components/ResultsTable.jsx` — resumen y tabla de resultados.
- `frontend/src/components/PersonRow.jsx` — fila de persona (dentro de ResultsTable).
- `frontend/src/components/ErrorMessage.jsx` — visualización de errores.
- `frontend/src/tests/components.test.jsx` — 17 pruebas de componentes y API.
- `frontend/.eslintrc.cjs` — configuración de ESLint.
- `docs/semana14_trabajo_renzo.md` — esta bitácora.

Commits pendientes: push a `origin` (fork Rodo00) y apertura de PR contra
`retblast/conciliafecc` (rama base: `main`).

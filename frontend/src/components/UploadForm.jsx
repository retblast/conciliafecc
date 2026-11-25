import { useState, useCallback } from 'react'
import { SOURCES, sourceLabel } from '../api/client'

export default function UploadForm({ onConciliar, cargando, error }) {
  const [archivos, setArchivos] = useState({})

  const manejarCambioArchivo = useCallback((source, event) => {
    const file = event.target.files ? event.target.files[0] : null
    setArchivos((prev) => {
      const siguiente = { ...prev }
      if (file) {
        siguiente[source] = file
      } else {
        delete siguiente[source]
      }
      return siguiente
    })
  }, [])

  const todosSeleccionados = SOURCES.every((s) => Boolean(archivos[s]))

  const manejarConciliar = useCallback(() => {
    const completo = {}
    for (const source of SOURCES) {
      const file = archivos[source]
      if (!file) {
        return
      }
      completo[source] = file
    }
    onConciliar(completo)
  }, [archivos, onConciliar])

  return (
    <section aria-label="Carga de archivos Excel">
      <h2>Cargar los tres archivos Excel</h2>
      <p>
        Seleccione un archivo por dependencia. Todos deben ser de tipo
        <code>.xlsx</code>.
      </p>

      {error && (
        <div role="alert" className="aviso error">
          {error}
        </div>
      )}

      <div className="carga-form">
        {SOURCES.map((source) => {
          const file = archivos[source]
          return (
            <div key={source} className="campo-archivo">
              <label htmlFor={`archivo-${source}`}>
                {sourceLabel(source)}
              </label>
              <input
                id={`archivo-${source}`}
                type="file"
                accept=".xlsx"
                onChange={(e) => manejarCambioArchivo(source, e)}
                disabled={cargando}
              />
              {file && (
                <span className="archivo-seleccionado">
                  {file.name} ({Math.round(file.size / 1024)} KB)
                </span>
              )}
            </div>
          )
        })}
      </div>

      <button
        type="button"
        className="btn-conciliar"
        disabled={cargando || !todosSeleccionados}
        onClick={manejarConciliar}
      >
        {cargando ? 'Conciliando…' : 'Conciliar archivos'}
      </button>
      {cargando && !todosSeleccionados && (
        <p className="ayuda">Espere a que termine la conciliación en curso.</p>
      )}
      {!cargando && !todosSeleccionados && (
        <p className="ayuda">
          Seleccione los tres archivos para habilitar la conciliación.
        </p>
      )}
    </section>
  )
}

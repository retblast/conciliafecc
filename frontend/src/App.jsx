import { useState, useCallback } from 'react'
import { conciliar } from './api/client'
import UploadForm from './components/UploadForm'
import ErrorMessage from './components/ErrorMessage'
import ResultsTable, { ResultSummary } from './components/ResultsTable'

export default function App() {
  const [cargando, setCargando] = useState(false)
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState(null)

  const manejarConciliar = useCallback(async (archivos) => {
    setCargando(true)
    setError(null)
    setResultado(null)
    try {
      const result = await conciliar(archivos)
      setResultado(result)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Error inesperado al conciliar los archivos.')
      }
    } finally {
      setCargando(false)
    }
  }, [])

  const manejarDescarga = useCallback(() => {
    if (!resultado) {
      return
    }
    const filas = ['Referencia,Aprobada,Faltantes,Duplicados,Inconsistencias']
    for (const persona of resultado.personas) {
      filas.push([
        persona.referencia,
        persona.aprobada ? 'Sí' : 'No',
        persona.faltantes.join(';'),
        persona.duplicados.join(';'),
        persona.inconsistencias.join(';'),
      ].join(','))
    }
    const csv = filas.join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = 'conciliafecc_resultados.csv'
    enlace.click()
    URL.revokeObjectURL(url)
  }, [resultado])

  return (
    <div className="app">
      <header>
        <h1>ConciliaFECC</h1>
        <p>Conciliación de registros de URA, Biblioteca y Constancia de No Adeudos</p>
      </header>

      <main>
        <UploadForm
          onConciliar={manejarConciliar}
          cargando={cargando}
          error={error}
        />

        {cargando && !error && !resultado && (
          <p className="estado-carga">Procesando los archivos, por favor espere…</p>
        )}

        {!cargando && resultado && (
          <>
            <ResultSummary
              registros={resultado.registros_por_fuente}
              aprobados={resultado.aprobados}
              faltantes={resultado.faltantes_por_fuente}
              advertencias={resultado.advertencias}
            />
            <ResultsTable personas={resultado.personas} />
            <button
              type="button"
              className="btn-conciliar"
              onClick={manejarDescarga}
            >
              Descargar resultados (CSV)
            </button>
            <p className="ayuda">
              La descarga del Excel consolidado (.xlsx) está pendiente de
              coordinación del contrato HTTP con el backend (ver
              docs/CONTRATO_API.md).
            </p>
          </>
        )}
      </main>

      {error && <ErrorMessage mensaje={error} />}
    </div>
  )
}

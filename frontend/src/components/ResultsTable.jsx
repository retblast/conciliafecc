import { SOURCES, sourceLabel } from '../api/client'

export function ResultSummary({ registros, aprobados, faltantes, advertencias }) {
  return (
    <section className="resumen">
      <h2>Resumen de la conciliación</h2>
      <table className="tabla-resumen">
        <thead>
          <tr>
            <th>Fuente</th>
            <th>Registros</th>
            <th>Personas faltantes</th>
          </tr>
        </thead>
        <tbody>
          {SOURCES.map((source) => (
            <tr key={source}>
              <td>{sourceLabel(source)}</td>
              <td>{registros[source]}</td>
              <td>{faltantes[source]}</td>
            </tr>
          ))}
          <tr className="total">
            <td colSpan="2">Personas aprobadas</td>
            <td>{aprobados}</td>
          </tr>
        </tbody>
      </table>

      {advertencias.length > 0 && (
        <div className="advertencias">
          <h3>Advertencias</h3>
          <ul>
            {advertencias.map((texto, i) => (
              <li key={i}>{texto}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function PersonRow({ persona }) {
  const faltantesTexto =
    persona.faltantes.length > 0
      ? persona.faltantes.map(sourceLabel).join(', ')
      : '—'
  const duplicadosTexto =
    persona.duplicados.length > 0
      ? persona.duplicados.map(sourceLabel).join(', ')
      : '—'
  const inconsistenciasTexto =
    persona.inconsistencias.length > 0
      ? persona.inconsistencias.join('; ')
      : '—'

  return (
    <tr className={persona.aprobada ? 'aprobada' : 'observada'}>
      <td>{persona.referencia}</td>
      <td>{persona.aprobada ? 'Sí' : 'No'}</td>
      <td>{faltantesTexto}</td>
      <td>{duplicadosTexto}</td>
      <td>{inconsistenciasTexto}</td>
    </tr>
  )
}

export default function ResultsTable({ personas }) {
  const aprobadas = personas.filter((p) => p.aprobada).length
  const observadas = personas.length - aprobadas

  return (
    <section aria-label="Resultados de conciliación">
      <h2>Personas</h2>
      <p>
        {personas.length} persona(s) evaluada(s): {aprobadas} aprobada(s) y{' '}
        {observadas} con observaciones.
      </p>
      <table className="tabla-personas">
        <thead>
          <tr>
            <th>Referencia</th>
            <th>Aprobada</th>
            <th>Faltantes</th>
            <th>Duplicados</th>
            <th>Inconsistencias</th>
          </tr>
        </thead>
        <tbody>
          {personas.length === 0 ? (
            <tr>
              <td colSpan="5">No hay personas en el resultado.</td>
            </tr>
          ) : (
            personas.map((persona) => (
              <PersonRow key={persona.referencia} persona={persona} />
            ))
          )}
        </tbody>
      </table>
    </section>
  )
}

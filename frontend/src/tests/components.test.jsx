import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import UploadForm from '../components/UploadForm'
import ResultsTable, { ResultSummary } from '../components/ResultsTable'
import ErrorMessage from '../components/ErrorMessage'
import { conciliar, SOURCES, sourceLabel } from '../api/client'

const crearArchivo = (nombre = 'prueba.xlsx', tipo = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') =>
  new File(['contenido-sintetico'], nombre, { type: tipo })

describe('sourceLabel', () => {
  it('devuelve la etiqueta legible de cada fuente', () => {
    expect(sourceLabel('ura')).toBe('URA')
    expect(sourceLabel('biblioteca')).toBe('Biblioteca')
    expect(sourceLabel('no_adeudos')).toBe('Constancia de No Adeudos')
  })
})

describe('UploadForm', () => {
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('muestra tres inputs de archivo etiquetados por fuente', () => {
    render(<UploadForm onConciliar={vi.fn()} cargando={false} error={null} />)
    SOURCES.forEach((source) => {
      expect(screen.getByLabelText(sourceLabel(source))).toBeInTheDocument()
    })
  })

  it('acepta solo archivos .xlsx', () => {
    const { container } = render(
      <UploadForm onConciliar={vi.fn()} cargando={false} error={null} />,
    )
    SOURCES.forEach((source) => {
      const input = container.querySelector(`#archivo-${source}`)
      expect(input).toHaveAttribute('accept', '.xlsx')
    })
  })

  it('el botón Conciliar está deshabilitado si falta algún archivo', () => {
    render(<UploadForm onConciliar={vi.fn()} cargando={false} error={null} />)
    const boton = screen.getByRole('button', { name: /conciliar archivos/i })
    expect(boton).toBeDisabled()
  })

  it('habilita el botón cuando los tres archivos están seleccionados', () => {
    const onConciliar = vi.fn()
    render(<UploadForm onConciliar={onConciliar} cargando={false} error={null} />)
    SOURCES.forEach((source) => {
      const input = screen.getByLabelText(sourceLabel(source))
      fireEvent.change(input, {
        target: { files: [crearArchivo(`${source}.xlsx`)] },
      })
    })
    const boton = screen.getByRole('button', { name: /conciliar archivos/i })
    expect(boton).not.toBeDisabled()
  })

  it('llama a onConciliar con los tres archivos al pulsar el botón', () => {
    const onConciliar = vi.fn()
    render(<UploadForm onConciliar={onConciliar} cargando={false} error={null} />)
    SOURCES.forEach((source) => {
      const input = screen.getByLabelText(sourceLabel(source))
      fireEvent.change(input, {
        target: { files: [crearArchivo(`${source}.xlsx`)] },
      })
    })
    fireEvent.click(screen.getByRole('button', { name: /conciliar archivos/i }))
    expect(onConciliar).toHaveBeenCalledTimes(1)
    const args = onConciliar.mock.calls[0][0]
    SOURCES.forEach((source) => {
      expect(args[source]).toBeInstanceOf(File)
      expect(args[source].name).toBe(`${source}.xlsx`)
    })
  })

  it('muestra el nombre y tamaño del archivo seleccionado', () => {
    render(<UploadForm onConciliar={vi.fn()} cargando={false} error={null} />)
    const input = screen.getByLabelText(sourceLabel('ura'))
    fireEvent.change(input, {
      target: { files: [crearArchivo('ura.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')] },
    })
    expect(screen.getByText(/ura.xlsx/)).toBeInTheDocument()
    expect(screen.getByText(/KB/)).toBeInTheDocument()
  })

  it('deshabilita el botón mientras se está cargando', () => {
    render(<UploadForm onConciliar={vi.fn()} cargando={true} error={null} />)
    const boton = screen.getByRole('button', { name: /conciliando/i })
    expect(boton).toBeDisabled()
  })

  it('muestra un aviso de error cuando se proporciona uno', () => {
    render(
      <UploadForm
        onConciliar={vi.fn()}
        cargando={false}
        error="El archivo de Biblioteca no es válido."
      />,
    )
    expect(screen.getByRole('alert')).toHaveTextContent(
      /El archivo de Biblioteca no es válido./i,
    )
  })
})

describe('ResultSummary', () => {
  it('muestra los registros, aprobados y faltantes por fuente', () => {
    render(
      <ResultSummary
        registros={{ ura: 10, biblioteca: 8, no_adeudos: 12 }}
        aprobados={5}
        faltantes={{ ura: 2, biblioteca: 3, no_adeudos: 1 }}
        advertencias={[]}
      />,
    )
    expect(screen.getByText('URA')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('muestra las advertencias si las hay', () => {
    const advertencias = ['Referencia duplicada detectada en URA.']
    render(
      <ResultSummary
        registros={{ ura: 1, biblioteca: 1, no_adeudos: 1 }}
        aprobados={0}
        faltantes={{ ura: 0, biblioteca: 0, no_adeudos: 0 }}
        advertencias={advertencias}
      />,
    )
    expect(screen.getByText(/Referencia duplicada detectada en URA./)).toBeInTheDocument()
  })
})

describe('ResultsTable', () => {
  it('muestra la tabla de personas con sus columnas', () => {
    render(
      <ResultsTable
        personas={[
          {
            referencia: 'PER-001',
            aprobada: true,
            faltantes: [],
            duplicados: [],
            inconsistencias: [],
          },
          {
            referencia: 'PER-002',
            aprobada: false,
            faltantes: ['biblioteca'],
            duplicados: [],
            inconsistencias: ['DNI con formato inválido.'],
          },
        ]}
      />,
    )
    expect(screen.getByText('PER-001')).toBeInTheDocument()
    expect(screen.getByText('PER-002')).toBeInTheDocument()
    expect(screen.getByText('Sí')).toBeInTheDocument()
    expect(screen.getByText('No')).toBeInTheDocument()
    expect(screen.getByText(/Biblioteca/)).toBeInTheDocument()
    expect(screen.getByText(/DNI con formato inválido./)).toBeInTheDocument()
  })

  it('muestra guión cuando no hay faltantes ni duplicados', () => {
    render(
      <ResultsTable
        personas={[
          {
            referencia: 'PER-001',
            aprobada: true,
            faltantes: [],
            duplicados: [],
            inconsistencias: [],
          },
        ]}
      />,
    )
    const filas = screen.getAllByRole('row')
    const celdasFaltantes = filas[1].querySelectorAll('td')[2]
    expect(celdasFaltantes).toHaveTextContent('—')
  })

  it('indica cuántas personas están aprobadas y observadas', () => {
    render(
      <ResultsTable
        personas={[
          { referencia: 'A', aprobada: true, faltantes: [], duplicados: [], inconsistencias: [] },
          { referencia: 'B', aprobada: false, faltantes: ['ura'], duplicados: [], inconsistencias: [] },
          { referencia: 'C', aprobada: false, faltantes: [], duplicados: ['biblioteca'], inconsistencias: [] },
        ]}
      />,
    )
    expect(document.body.textContent).toMatch(/3 persona\(s\) evaluada\(s\): 1 aprobada\(s\) y 2 con observaciones\./)
  })
})

describe('ErrorMessage', () => {
  it('muestra el mensaje en un role="alert"', () => {
    render(<ErrorMessage mensaje="Error de conexión con la API." />)
    expect(screen.getByRole('alert')).toHaveTextContent(/Error de conexión con la API\./)
  })
})

describe('API client - conciliar', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('envía los tres archivos como multipart/form-data y devuelve el resultado', async () => {
    const resultadoEsperado = {
      registros_por_fuente: { ura: 10, biblioteca: 8, no_adeudos: 12 },
      aprobados: 5,
      faltantes_por_fuente: { ura: 2, biblioteca: 3, no_adeudos: 1 },
      personas: [
        {
          referencia: 'PER-001',
          aprobada: true,
          faltantes: [],
          duplicados: [],
          inconsistencias: [],
        },
      ],
      advertencias: [],
    }
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify(resultadoEsperado), { status: 200 }),
    )

    const archivos = {
      ura: crearArchivo('ura.xlsx'),
      biblioteca: crearArchivo('biblioteca.xlsx'),
      no_adeudos: crearArchivo('no_adeudos.xlsx'),
    }
    const resultado = await conciliar(archivos)

    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/api/v1/validaciones')
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
    expect(resultado.aprobados).toBe(5)
    expect(resultado.personas[0].referencia).toBe('PER-001')
  })

  it('lanza un error con el mensaje de la API cuando falla', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(
        JSON.stringify({ error: { codigo: 'xlsx_invalido', mensaje: 'El archivo de Biblioteca no es válido.', fuente: 'biblioteca' } }),
        { status: 422 },
      ),
    )

    const archivos = {
      ura: crearArchivo('ura.xlsx'),
      biblioteca: crearArchivo('biblioteca.xlsx'),
      no_adeudos: crearArchivo('no_adeudos.xlsx'),
    }

    await expect(conciliar(archivos)).rejects.toThrow(
      /El archivo de Biblioteca no es válido./i,
    )
  })
})

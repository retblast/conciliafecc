export default function ErrorMessage({ mensaje }) {
  return (
    <div role="alert" className="aviso error">
      {mensaje}
    </div>
  )
}

export default function Badge({ type = '', children }) {
  return <span className={type ? `severity ${type}` : 'severity'}>{children}</span>
}

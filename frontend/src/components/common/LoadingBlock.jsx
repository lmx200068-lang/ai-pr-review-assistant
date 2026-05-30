import EmptyState from './EmptyState'

export default function LoadingBlock({ children = 'Loading' }) {
  return <EmptyState>{children}</EmptyState>
}

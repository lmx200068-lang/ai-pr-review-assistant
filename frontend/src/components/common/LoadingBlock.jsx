import EmptyState from './EmptyState'

export default function LoadingBlock({ children = '正在加载' }) {
  return <EmptyState>{children}</EmptyState>
}

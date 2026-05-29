import { useEffect, useRef, useState } from 'react'
import { getReviewTask } from '../api/client'
import { isTerminalTask, normalizeTask } from '../utils/formatters'

export function useReviewTaskPolling(
  taskId,
  enabled = true,
  intervalMs = 1500,
) {
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const stoppedRef = useRef(false)

  useEffect(() => {
    if (!taskId || !enabled) {
      return undefined
    }

    stoppedRef.current = false
    let timer = null

    async function poll() {
      if (stoppedRef.current) {
        return
      }
      setLoading(true)
      try {
        const nextTask = normalizeTask(await getReviewTask(taskId))
        setTask(nextTask)
        setError('')
        if (isTerminalTask(nextTask)) {
          stoppedRef.current = true
          return
        }
      } catch (requestError) {
        setError(requestError.message)
      } finally {
        setLoading(false)
      }

      if (!stoppedRef.current) {
        timer = window.setTimeout(poll, intervalMs)
      }
    }

    poll()

    return () => {
      stoppedRef.current = true
      if (timer) {
        window.clearTimeout(timer)
      }
    }
  }, [enabled, intervalMs, taskId])

  return {
    task,
    loading,
    error,
    stop: () => {
      stoppedRef.current = true
    },
  }
}

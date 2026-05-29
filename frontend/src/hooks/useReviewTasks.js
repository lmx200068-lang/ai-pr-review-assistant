import { useCallback, useEffect, useState } from 'react'
import {
  createReviewTask,
  getReviewTask,
  listReviewTasks,
} from '../api/client'
import {
  mergeTask,
  mergeTaskList,
  normalizeTask,
} from '../utils/formatters'

export function useReviewTasks() {
  const [tasks, setTasks] = useState([])
  const [activeTask, setActiveTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  const storeTask = useCallback((task) => {
    const normalizedTask = normalizeTask(task)
    setActiveTask((current) => mergeTask(current, normalizedTask))
    setTasks((current) => mergeTaskList(current, normalizedTask))
    return normalizedTask
  }, [])

  const refreshTasks = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listReviewTasks()
      const normalizedTasks = data.map(normalizeTask)
      setTasks((current) => mergeTaskList(current, normalizedTasks))
      setActiveTask((current) => current || normalizedTasks[0] || null)
      return normalizedTasks
    } catch (requestError) {
      setError(requestError.message)
      throw requestError
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshTask = useCallback(
    async (taskId) => {
      const task = await getReviewTask(taskId)
      return storeTask(task)
    },
    [storeTask],
  )

  const createTask = useCallback(
    async (payload) => {
      setCreating(true)
      setError('')
      try {
        const task = await createReviewTask(payload)
        return storeTask(task)
      } catch (requestError) {
        setError(requestError.message)
        throw requestError
      } finally {
        setCreating(false)
      }
    },
    [storeTask],
  )

  const selectTask = useCallback(
    (task) => {
      storeTask(task)
    },
    [storeTask],
  )

  useEffect(() => {
    refreshTasks().catch(() => {})
  }, [refreshTasks])

  return {
    tasks,
    activeTask,
    createTask,
    selectTask,
    refreshTask,
    refreshTasks,
    loading,
    creating,
    error,
  }
}

import { useCallback, useEffect, useState } from 'react'
import { getHealth } from '../api/client'

export function useHealth() {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getHealth()
      setHealth(data)
      return data
    } catch (requestError) {
      setError(requestError.message)
      throw requestError
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh().catch(() => {})
  }, [refresh])

  return { health, loading, error, refresh }
}

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactNode } from 'react'

// Mock hook for testing patterns
function useCounter(initialCount = 0) {
  const [count, setCount] = React.useState(initialCount)
  const increment = () => setCount(c => c + 1)
  const decrement = () => setCount(c => c - 1)
  return { count, increment, decrement }
}

import React from 'react'

describe('Hook Tests', () => {
  it('initializes counter with default value', () => {
    const { result } = renderHook(() => useCounter())
    expect(result.current.count).toBe(0)
  })

  it('initializes counter with provided value', () => {
    const { result } = renderHook(() => useCounter(5))
    expect(result.current.count).toBe(5)
  })

  it('increments counter', () => {
    const { result } = renderHook(() => useCounter())
    expect(result.current.count).toBe(0)

    result.current.increment()
    expect(result.current.count).toBe(1)

    result.current.increment()
    expect(result.current.count).toBe(2)
  })

  it('decrements counter', () => {
    const { result } = renderHook(() => useCounter(5))
    expect(result.current.count).toBe(5)

    result.current.decrement()
    expect(result.current.count).toBe(4)
  })
})

describe('Query Hook Tests', () => {
  const createWrapper = () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })

    return ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    )
  }

  it('handles loading state in query', async () => {
    const mockData = { id: 1, name: 'Event 1' }

    // Mock query hook
    const useEventQuery = vi.fn(() => ({
      data: undefined,
      isLoading: true,
      error: null,
    }))

    const { result } = renderHook(() => useEventQuery(), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
    expect(result.current.data).toBeUndefined()
  })

  it('handles success state in query', async () => {
    const mockData = { id: 1, name: 'Event 1' }

    const useEventQuery = vi.fn(() => ({
      data: mockData,
      isLoading: false,
      error: null,
    }))

    const { result } = renderHook(() => useEventQuery(), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.data).toEqual(mockData)
  })

  it('handles error state in query', async () => {
    const error = new Error('Failed to fetch')

    const useEventQuery = vi.fn(() => ({
      data: undefined,
      isLoading: false,
      error,
    }))

    const { result } = renderHook(() => useEventQuery(), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeDefined()
    expect(result.current.error?.message).toBe('Failed to fetch')
  })
})

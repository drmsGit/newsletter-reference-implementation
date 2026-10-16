import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import AIButton from './AIButton'

afterEach(() => vi.useRealTimers())

describe('the AI button (task-100)', () => {
  it('asks once: presses while the model works are ignored, and focus stays', () => {
    const onPress = vi.fn()
    const { rerender } = render(<AIButton onPress={onPress} pending={false}>Suggest with AI</AIButton>)
    fireEvent.click(screen.getByRole('button', { name: 'Suggest with AI' }))
    rerender(<AIButton onPress={onPress} pending>Suggest with AI</AIButton>)
    const busy = screen.getByRole('button', { name: 'Asking the model…' })
    busy.focus()
    fireEvent.click(busy)
    expect(onPress).toHaveBeenCalledTimes(1)
    expect(busy).toHaveAttribute('aria-disabled', 'true')
    expect(busy).toHaveFocus()
  })

  it('counts the seconds after two, without changing its name every second', () => {
    vi.useFakeTimers()
    render(<AIButton onPress={() => {}} pending>Suggest with AI</AIButton>)
    const busy = screen.getByRole('button', { name: 'Asking the model…' })
    act(() => vi.advanceTimersByTime(1000))
    expect(busy).not.toHaveTextContent(/\d s/)
    act(() => vi.advanceTimersByTime(4000))
    expect(busy).toHaveTextContent('5 s')
    expect(screen.getByRole('button', { name: 'Asking the model…' })).toBe(busy)
  })

  it('says once that the model was asked, and starts the count afresh next time', () => {
    vi.useFakeTimers()
    const { rerender } = render(<AIButton onPress={() => {}} pending>Suggest with AI</AIButton>)
    expect(screen.getByRole('status')).toHaveTextContent('Asking the model…')
    act(() => vi.advanceTimersByTime(6000))
    rerender(<AIButton onPress={() => {}} pending={false}>Suggest with AI</AIButton>)
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
    expect(screen.getByRole('button', { name: 'Suggest with AI' })).not.toHaveAttribute('aria-disabled')
    rerender(<AIButton onPress={() => {}} pending>Suggest with AI</AIButton>)
    expect(screen.getByRole('button', { name: 'Asking the model…' })).not.toHaveTextContent(/\d s/)
  })
})

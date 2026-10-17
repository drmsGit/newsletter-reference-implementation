import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Personalisation, { PersonalisationEntry } from './Personalisation'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-16T09:00:00Z'
const FORMAL = {
  id: 5, name: 'salutation_formal', label: 'Salutation formal', updated_at: T,
  languages: {
    de: {
      cases: [
        { field: 'gender', is: 'equals', value: 'female', text: 'Sehr geehrte Frau {{last_name}},' },
        { field: 'gender', is: 'equals', value: 'male', text: 'Sehr geehrter Herr {{last_name}},' },
      ],
      fallback: 'Sehr geehrte Damen und Herren,',
    },
  },
}

function server(options: { mayManage?: boolean; deleteRefused?: string } = {}) {
  const writes: Request[] = []
  const handlers = {
    'GET /expressions': () => jsonResponse({ items: [FORMAL], may_manage: options.mayManage ?? true }),
    'POST /expressions': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ ...FORMAL, id: 6, name: 'greeting' }, 201)
    },
    'PUT /expressions/5': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse({ ...FORMAL, updated_at: '2026-10-16T09:01:00Z' })
    },
    'DELETE /expressions/5': (request: Request) => {
      writes.push(request.clone())
      return options.deleteRefused ? jsonResponse({ detail: options.deleteRefused }, 409) : new Response(null, { status: 204 })
    },
  }
  return { handlers, writes }
}

function open(route: string, options = {}) {
  const { handlers, writes } = server(options)
  stubFetch(handlers as never)
  renderWithProviders(
    <Routes>
      <Route path="/settings/personalisation" element={<Personalisation />} />
      <Route path="/settings/personalisation/:id" element={<PersonalisationEntry />} />
    </Routes>,
    { route },
  )
  return writes
}

describe('the expression dictionary (task-365; ADR-199)', () => {
  it('lists the entries with how a text writes them', async () => {
    open('/settings/personalisation')
    expect(await screen.findByText('Salutation formal')).toBeInTheDocument()
    expect(screen.getByText('{{salutation_formal}}')).toBeInTheDocument()
  })

  it('creates an entry with its first language and fallback', async () => {
    const writes = open('/settings/personalisation')
    // "New entry" opens a dialog (task-372, decision 22).
    fireEvent.click(await screen.findByRole('button', { name: 'New entry' }))
    expect(await screen.findByRole('dialog', { name: 'New entry' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/^Name in a text/), { target: { value: 'greeting' } })
    fireEvent.change(screen.getByLabelText(/^Label/), { target: { value: 'Greeting' } })
    fireEvent.change(screen.getByLabelText(/^Text when nothing is known/), { target: { value: 'Hallo,' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({
      name: 'greeting', label: 'Greeting', languages: { de: { cases: [], fallback: 'Hallo,' } },
    })
  })

  it('saves label and cases with the version it read, and keeps the name', async () => {
    const writes = open('/settings/personalisation/5')
    const fallback = await screen.findByLabelText('Otherwise write (de)')
    fireEvent.change(fallback, { target: { value: 'Guten Tag,' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add a case' }))
    const added = within(screen.getByRole('group', { name: 'de case 3' }))
    fireEvent.change(added.getByLabelText('Write'), { target: { value: 'Hallo {{first_name}},' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(writes[0].headers.get('If-Match')).toBe(T)
    const body = await writes[0].json()
    expect(body.name).toBeUndefined()
    expect(body.languages.de.fallback).toBe('Guten Tag,')
    expect(body.languages.de.cases[2]).toEqual({ field: 'first_name', is: 'filled', text: 'Hallo {{first_name}},' })
  })

  it('shows where an entry is still used when deleting is refused', async () => {
    open('/settings/personalisation/5', { deleteRefused: '{{salutation_formal}} is still used: content record “Spring”.' })
    fireEvent.click(await screen.findByRole('button', { name: 'Delete…' }))
    fireEvent.click(screen.getByRole('button', { name: 'Delete Salutation formal' }))
    expect(await screen.findByText(/still used: content record “Spring”/)).toBeInTheDocument()
  })

  it('is read-only for someone who may not change it', async () => {
    open('/settings/personalisation/5', { mayManage: false })
    expect(await screen.findByLabelText('Otherwise write (de)')).toHaveAttribute('readonly')
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add a case' })).not.toBeInTheDocument()
  })
})

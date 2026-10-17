import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import Content from './Content'
import { ShortcutsProvider } from '../shortcuts/Shortcuts'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

function open({ refuse }: { refuse?: number } = {}, { shortcuts = false } = {}) {
  const writes: Request[] = []
  stubFetch({
    'GET /content/': () => jsonResponse(page([])),
    'GET /content/fields': () => jsonResponse([]),
    'GET /content/categories': () => jsonResponse([]),
    'GET /content/category-relations': () => jsonResponse([]),
    'POST /content/': (request: Request) => {
      writes.push(request.clone())
      return refuse ? jsonResponse({ detail: 'no' }, refuse) : jsonResponse({ id: 77, title: 'x', content: {} })
    },
  } as never)
  const routes = (
    <Routes>
      <Route path="/content/records" element={<Content />} />
      <Route path="/content/:id" element={<h1>Record page</h1>} />
    </Routes>
  )
  renderWithProviders(shortcuts ? <ShortcutsProvider>{routes}</ShortcutsProvider> : routes, { route: '/content/records' })
  return writes
}

const dialog = () => screen.findByRole('dialog', { name: 'New content record' })

describe('creating a record (task-281)', () => {
  it('asks for a title and a description only, creates, and opens the new record', async () => {
    const writes = open()
    fireEvent.click(await screen.findByRole('button', { name: /New record/ }))
    const form = await dialog()
    expect(within(form).getAllByRole('textbox')).toHaveLength(2)
    fireEvent.change(within(form).getByLabelText(/^Title/), { target: { value: '  Lisbon in spring ' } })
    fireEvent.change(within(form).getByLabelText('Description'), { target: { value: 'Three days' } })
    fireEvent.submit(within(form).getByLabelText(/^Title/).closest('form')!)
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ title: 'Lisbon in spring', description: 'Three days', content: {} })
    expect(await screen.findByRole('heading', { name: 'Record page' })).toBeInTheDocument()
  })

  it('sends no description when none is given, and needs a title', async () => {
    const writes = open()
    fireEvent.click(await screen.findByRole('button', { name: /New record/ }))
    const form = await dialog()
    expect(within(form).getByRole('button', { name: 'Create' })).toBeDisabled()
    fireEvent.change(within(form).getByLabelText(/^Title/), { target: { value: 'Porto' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Create' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ title: 'Porto', description: null, content: {} })
  })

  it('says so in place when the server refuses, and stays open', async () => {
    open({ refuse: 403 })
    fireEvent.click(await screen.findByRole('button', { name: /New record/ }))
    const form = await dialog()
    fireEvent.change(within(form).getByLabelText(/^Title/), { target: { value: 'Porto' } })
    fireEvent.click(within(form).getByRole('button', { name: 'Create' }))
    expect(await within(form).findByRole('alert')).toHaveTextContent('You do not have permission to create content')
    expect(screen.queryByRole('heading', { name: 'Record page' })).not.toBeInTheDocument()
  })

  it('is laid out as every create dialog: heading above the form, Cancel then Create at its foot (task-392 item 8)', async () => {
    open()
    fireEvent.click(await screen.findByRole('button', { name: /New record/ }))
    const form = (await dialog()).querySelector('form')!
    expect(form).toHaveClass('dialog-form')
    expect(within(form).queryByRole('heading')).not.toBeInTheDocument()
    const actions = within(form).getAllByRole('button').map((b) => b.textContent)
    expect(actions).toEqual(['Cancel', 'Create'])
    expect(within(form).getByRole('button', { name: 'Create' }).parentElement).toHaveClass('dialog-actions')
  })

  it('opens with n, is listed in the shortcut overview, and closes on Esc', async () => {
    open({}, { shortcuts: true })
    await screen.findByRole('button', { name: /New record/ })
    fireEvent.keyDown(document.body, { key: '?' })
    const overview = await screen.findByRole('dialog', { name: 'Keyboard shortcuts' })
    expect(within(overview).getByText('New content record')).toBeInTheDocument()
    fireEvent.keyDown(overview, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Keyboard shortcuts' })).not.toBeInTheDocument())
    fireEvent.keyDown(document.body, { key: 'n' })
    const form = await dialog()
    expect(within(form).getByLabelText(/^Title/)).toHaveFocus()
    fireEvent.keyDown(within(form).getByLabelText(/^Title/), { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'New content record' })).not.toBeInTheDocument())
  })
})

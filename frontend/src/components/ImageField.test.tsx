import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ImageField from './ImageField'
import { AutosaveField } from './EditorFields'
import { A_SESSION, jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-15T09:00:00Z'

function asset(id: number, extra: object = {}) {
  return {
    id, brand_id: 1, name: `acme-20261015-${id}-120x80-beach.png`, label: `Beach ${id}`, product_id: null,
    media_type: 'image/png', size_bytes: 2048, width: 120, height: 80, alt_text: 'A beach at noon',
    reference: `asset:${id}`, url: `http://localhost:8000/media/token${id}`, hidden: false,
    created_at: T, updated_at: T, ...extra,
  }
}

function server(options: { total?: number } = {}) {
  const writes: Request[] = []
  const reads: URL[] = []
  const handlers = {
    'GET /auth/session': () => jsonResponse(A_SESSION),
    'GET /assets/7': () => jsonResponse(asset(7)),
    'GET /assets/': (request: Request) => {
      const url = new URL(request.url)
      reads.push(url)
      const items = url.searchParams.get('brand') === '2'
        ? [asset(30, { brand_id: 2, label: 'Their logo' })]
        : [asset(9, { label: 'Lighthouse' })]
      return jsonResponse({ items, total: options.total ?? items.length, limit: 50, offset: 0 })
    },
    'POST /assets/30/copy': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse(asset(31, { label: 'Their logo' }), 201)
    },
    'POST /assets/9/hide': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse(asset(9, { hidden: true }))
    },
    'PUT /assets/9/alt': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse(asset(9, { alt_text: 'Lighthouse at dusk' }))
    },
  }
  return { handlers, writes, reads }
}

function open(value: string, options = {}) {
  const { handlers, writes, reads } = server(options)
  stubFetch(handlers as never)
  const onChange = vi.fn()
  renderWithProviders(<ImageField label="Image" value={value} onChange={onChange} />)
  return { onChange, writes, reads }
}

async function openPicker() {
  fireEvent.click(screen.getByRole('button', { name: /(Choose|Change) image/ }))
  return within(await screen.findByRole('dialog'))
}

describe('an image field (task-112; ADR-197)', () => {
  it('shows only the image, its name and alt text, and two buttons in the form', async () => {
    open('asset:7')
    expect(await screen.findByText('acme-20261015-7-120x80-beach.png')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'A beach at noon' })).toHaveAttribute('src', 'http://localhost:8000/media/token7')
    expect(screen.getByRole('button', { name: 'Change image…' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remove' })).toBeInTheDocument()
    expect(screen.queryByLabelText(/Replace the file/)).not.toBeInTheDocument()
  })

  it('picks from the library in a pop-in, checking the image before using it', async () => {
    const { onChange } = open('')
    const dialog = await openPicker()
    fireEvent.click(await dialog.findByRole('button', { name: /Lighthouse/ }))
    expect(dialog.getByText('acme-20261015-9-120x80-beach.png')).toBeInTheDocument()
    fireEvent.click(dialog.getByRole('button', { name: 'Use this image' }))
    expect(onChange).toHaveBeenCalledWith('asset:9')
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it("copies another brand's image into this brand when it is used", async () => {
    const { onChange, writes, reads } = open('')
    const dialog = await openPicker()
    fireEvent.click(await dialog.findByRole('button', { name: /Brand/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'Beta' }))
    fireEvent.click(await dialog.findByRole('button', { name: /Their logo/ }))
    expect(reads.some((url) => url.searchParams.get('brand') === '2')).toBe(true)
    fireEvent.click(dialog.getByRole('button', { name: 'Copy into Acme and use' }))
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('asset:31'))
    expect(new URL(writes[0].url).pathname).toBe('/assets/30/copy')
  })

  it('keeps the less common actions behind More, and they act on the image', async () => {
    const { writes } = open('')
    const dialog = await openPicker()
    fireEvent.click(await dialog.findByRole('button', { name: /Lighthouse/ }))
    fireEvent.click(dialog.getByText('More: alt text, replace, hide'))
    fireEvent.change(dialog.getByLabelText('Alt text'), { target: { value: 'Lighthouse at dusk' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Save alt text' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(await writes[0].json()).toEqual({ alt_text: 'Lighthouse at dusk' })
    fireEvent.click(dialog.getByRole('button', { name: 'Hide from the library' }))
    await waitFor(() => expect(writes).toHaveLength(2))
    expect(new URL(writes[1].url).pathname).toBe('/assets/9/hide')
  })

  it('loads more when the library holds more than it shows', async () => {
    const { reads } = open('', { total: 120 })
    const dialog = await openPicker()
    fireEvent.click(await dialog.findByRole('button', { name: 'Load more' }))
    await waitFor(() => expect(reads.some((url) => Number(url.searchParams.get('limit')) > 50)).toBe(true))
  })

  it('takes an outside address for images kept elsewhere', async () => {
    const { onChange } = open('')
    const dialog = await openPicker()
    fireEvent.click(dialog.getByRole('tab', { name: 'Web address' }))
    expect(dialog.queryByLabelText('Alt text')).not.toBeInTheDocument()
    fireEvent.change(await dialog.findByLabelText('Image address'), { target: { value: 'https://cdn.example.org/a.jpg' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Use this address' }))
    expect(onChange).toHaveBeenCalledWith('https://cdn.example.org/a.jpg')
  })

  it('asks for alt text with an address when the field keeps one, and hands both back (ADR-197)', async () => {
    const { handlers } = server()
    stubFetch(handlers as never)
    const onChange = vi.fn()
    renderWithProviders(<ImageField label="Image" value="" alt="" onChange={onChange} />)
    const dialog = await openPicker()
    fireEvent.click(dialog.getByRole('tab', { name: 'Web address' }))
    fireEvent.change(await dialog.findByLabelText('Image address'), { target: { value: 'https://cdn.example.org/a.jpg' } })
    fireEvent.change(dialog.getByLabelText('Alt text'), { target: { value: 'A red door' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Use this address' }))
    expect(onChange).toHaveBeenCalledWith('https://cdn.example.org/a.jpg', 'A red door')
  })

  it('never asks for alt text for a library image: it has its own', async () => {
    const { handlers } = server()
    stubFetch(handlers as never)
    const onChange = vi.fn()
    renderWithProviders(<ImageField label="Image" value="" alt="Old words" onChange={onChange} />)
    const dialog = await openPicker()
    fireEvent.click(await dialog.findByRole('button', { name: /Lighthouse/ }))
    fireEvent.click(dialog.getByRole('button', { name: 'Use this image' }))
    expect(onChange).toHaveBeenCalledWith('asset:9')
  })

  it('removes the image', async () => {
    const { onChange } = open('asset:7')
    fireEvent.click(await screen.findByRole('button', { name: 'Remove' }))
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('is what an editor field of type image shows, saving a pick at once', async () => {
    stubFetch(server().handlers as never)
    const onSave = vi.fn()
    renderWithProviders(
      <AutosaveField field={{ name: 'image_url', label: 'Image', type: 'image' }} value="" onSave={onSave} error={undefined} />,
    )
    const dialog = await openPicker()
    fireEvent.click(await dialog.findByRole('button', { name: /Lighthouse/ }))
    fireEvent.click(dialog.getByRole('button', { name: 'Use this image' }))
    expect(onSave).toHaveBeenCalledWith('asset:9')
  })

  it('saves an address and its alt text in one write, the alt field never shown on its own', async () => {
    stubFetch(server().handlers as never)
    const onSave = vi.fn()
    renderWithProviders(
      <AutosaveField field={{ name: 'image_url', label: 'Image', type: 'image', alt: 'image_alt' }} value=""
        alt="" onSave={onSave} error={undefined} />,
    )
    const dialog = await openPicker()
    fireEvent.click(dialog.getByRole('tab', { name: 'Web address' }))
    fireEvent.change(await dialog.findByLabelText('Image address'), { target: { value: 'https://cdn.example.org/a.jpg' } })
    fireEvent.change(dialog.getByLabelText('Alt text'), { target: { value: 'A red door' } })
    fireEvent.click(dialog.getByRole('button', { name: 'Use this address' }))
    expect(onSave).toHaveBeenCalledWith('https://cdn.example.org/a.jpg', { image_alt: 'A red door' })
  })
})

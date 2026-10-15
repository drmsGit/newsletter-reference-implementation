import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ImageField from './ImageField'
import { AutosaveField } from './EditorFields'
import { jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

const T = '2026-10-15T09:00:00Z'

function asset(id: number, extra: object = {}) {
  return {
    id, name: `acme-20261015-${id}-120x80-beach.png`, label: 'Beach', product_id: null, media_type: 'image/png',
    size_bytes: 100, width: 120, height: 80, alt_text: 'A beach at noon', reference: `asset:${id}`,
    url: `http://localhost:8000/media/token${id}`, hidden: false, created_at: T, updated_at: T, ...extra,
  }
}

function server() {
  const writes: Request[] = []
  const handlers = {
    'GET /assets/7': () => jsonResponse(asset(7)),
    'GET /assets/': () => jsonResponse(page([asset(9, { name: 'acme-20261015-9-640x480-lighthouse.jpg' })])),
    'POST /assets/': async (request: Request) => {
      writes.push(request.clone())
      return jsonResponse(asset(12, { name: 'acme-20261015-12-120x80-dunes.png' }), 201)
    },
    'POST /assets/9/hide': (request: Request) => {
      writes.push(request.clone())
      return jsonResponse(asset(9, { hidden: true }))
    },
  }
  return { handlers, writes }
}

function open(value: string, onChange = vi.fn()) {
  const { handlers, writes } = server()
  stubFetch(handlers as never)
  renderWithProviders(<ImageField label="Image" value={value} onChange={onChange} />)
  return { onChange, writes }
}

describe('an image field (task-112; ADR-197)', () => {
  it('shows the chosen library image with its name and alt text', async () => {
    open('asset:7')
    expect(await screen.findByText('acme-20261015-7-120x80-beach.png')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'A beach at noon' })).toHaveAttribute('src', 'http://localhost:8000/media/token7')
  })

  it('picks an image from the library, storing its reference', async () => {
    const { onChange } = open('')
    expect(screen.getByText('No image.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Choose or upload…' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Use' }))
    expect(onChange).toHaveBeenCalledWith('asset:9')
  })

  it('hides an image from the library', async () => {
    const { writes } = open('')
    fireEvent.click(screen.getByRole('button', { name: 'Choose or upload…' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Hide from the library' }))
    await waitFor(() => expect(writes).toHaveLength(1))
    expect(new URL(writes[0].url).pathname).toBe('/assets/9/hide')
  })

  it('takes an outside address for images kept elsewhere', async () => {
    const { onChange } = open('')
    fireEvent.click(screen.getByRole('button', { name: 'Use a web address' }))
    fireEvent.change(screen.getByLabelText('Image address'), { target: { value: ' https://cdn.example.org/a.jpg ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Use this address' }))
    expect(onChange).toHaveBeenCalledWith('https://cdn.example.org/a.jpg')
  })

  it('removes the image', async () => {
    const { onChange } = open('asset:7')
    fireEvent.click(await screen.findByRole('button', { name: 'Remove image' }))
    expect(onChange).toHaveBeenCalledWith('')
  })

  it('is what an editor field of type image shows, saving a pick at once', async () => {
    const { handlers } = server()
    stubFetch(handlers as never)
    const onSave = vi.fn()
    renderWithProviders(
      <AutosaveField field={{ name: 'image_url', label: 'Image', type: 'image' }} value="" onSave={onSave} error={undefined} />,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Choose or upload…' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Use' }))
    expect(onSave).toHaveBeenCalledWith('asset:9')
  })
})

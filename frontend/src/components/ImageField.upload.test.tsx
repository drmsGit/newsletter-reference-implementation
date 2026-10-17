import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import ImageField from './ImageField'
import { A_SESSION, jsonResponse, page, renderWithProviders, stubFetch } from '../test-utils'

/*
 * The upload, with its hook replaced: in the test environment a multipart
 * body cannot be built (the test browser's FormData is not the one its
 * Request takes), so the request itself is checked live in a real browser.
 * What is pinned here is what the screen hands the upload and what it does
 * with the answer.
 */
const uploaded = vi.fn()
vi.mock('../api/resources', async (importOriginal) => {
  const original = await importOriginal<typeof import('../api/resources')>()
  return {
    ...original,
    useUploadAsset: () => ({
      isPending: false,
      error: null,
      mutate: (upload: unknown, options: { onSuccess: (asset: unknown) => void }) => {
        uploaded(upload)
        options.onSuccess({ id: 12, reference: 'asset:12' })
      },
    }),
  }
})

afterEach(() => vi.unstubAllGlobals())

describe('uploading from an image field (task-112)', () => {
  it('sends the file, what it shows and its alt text, then uses the new image', async () => {
    stubFetch({ 'GET /assets/': () => jsonResponse(page([])), 'GET /auth/session': () => jsonResponse(A_SESSION) } as never)
    const onChange = vi.fn()
    renderWithProviders(<ImageField label="Image" value="" onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Choose image…' }))
    fireEvent.click(await screen.findByRole('tab', { name: 'Upload new' }))
    const file = new File([new Uint8Array([137, 80, 78, 71])], 'dunes.png', { type: 'image/png' })
    // The app's own button opens the chooser; the browser's control is never shown (task-392 item 20).
    await screen.findByRole('button', { name: 'Choose a file…' })
    expect(screen.getByText('No file chosen')).toBeInTheDocument()
    const native = document.querySelector('.image-upload input[type="file"]') as HTMLInputElement
    expect(native).not.toBeVisible()
    expect(native).toHaveAttribute('accept', 'image/jpeg,image/png,image/gif,image/webp')
    fireEvent.change(native, { target: { files: [file] } })
    expect(screen.getByText('dunes.png')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload and use' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/What it shows/), { target: { value: ' Dunes ' } })
    fireEvent.change(screen.getByLabelText('Alt text'), { target: { value: 'Dunes at dusk' } })
    fireEvent.click(screen.getByRole('button', { name: 'Upload and use' }))
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('asset:12'))
    expect(uploaded).toHaveBeenCalledWith({ file, name: 'Dunes', alt_text: 'Dunes at dusk' })
  })
})

import { useState } from 'react'
import { Button, Input, Label, Text, TextField } from 'react-aria-components'

import {
  useAsset,
  useAssets,
  useHideAsset,
  useReplaceAsset,
  useUploadAsset,
  type Asset,
} from '../api/resources'
import { HttpError } from '../api/session'

/**
 * An image field: a library image of this brand, or an https address
 * (task-112; ADR-197 point 7).
 *
 * The field stores the image's reference (`asset:<id>`), never its address,
 * so alt text travels with the image and a replaced file shows wherever it is
 * used. The picker is search only, over names the server generates
 * (decision 5), with an upload beside it. An outside address is for images
 * that live in a DAM or CDN.
 */
export default function ImageField({
  label,
  value,
  onChange,
  required = false,
  readOnly = false,
  error,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  required?: boolean
  readOnly?: boolean
  error?: string
}) {
  const reference = /^asset:(\d+)$/.exec(value ?? '')
  const assetId = reference ? Number(reference[1]) : null
  const current = useAsset(assetId)
  const [mode, setMode] = useState<'closed' | 'library' | 'address'>('closed')
  const [address, setAddress] = useState(assetId == null ? value : '')

  return (
    <div className="field image-field" role="group" aria-label={label}>
      <p>
        <strong>{label}</strong>
        {required && <span className="muted"> (required)</span>}
      </p>
      {assetId != null && current.data && <Current asset={current.data} readOnly={readOnly} />}
      {assetId != null && current.isError && <p role="alert">This image is not in the library any more.</p>}
      {assetId == null && value && (
        <p>
          <img src={value} alt="" style={{ maxWidth: 160, maxHeight: 100 }} /> <span className="muted">{value}</span>
        </p>
      )}
      {!value && <p className="muted">No image.</p>}
      {!readOnly && (
        <p>
          <Button onPress={() => setMode(mode === 'library' ? 'closed' : 'library')}>Choose or upload…</Button>{' '}
          <Button onPress={() => setMode(mode === 'address' ? 'closed' : 'address')}>Use a web address</Button>
          {value && (
            <>
              {' '}
              <Button onPress={() => onChange('')}>Remove image</Button>
            </>
          )}
        </p>
      )}
      {mode === 'library' && (
        <Library
          onPick={(asset) => {
            onChange(asset.reference)
            setMode('closed')
          }}
        />
      )}
      {mode === 'address' && (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            onChange(address.trim())
            setMode('closed')
          }}
        >
          <TextField value={address} onChange={setAddress} type="url">
            <Label>Image address</Label>
            <Input />
            <Text slot="description" className="muted">
              A full address starting with https://, for images kept elsewhere.
            </Text>
          </TextField>
          <Button type="submit">Use this address</Button>
        </form>
      )}
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}
    </div>
  )
}

/** The chosen library image, with what can be done to it. */
function Current({ asset, readOnly }: { asset: Asset; readOnly: boolean }) {
  const replace = useReplaceAsset(asset.id)
  return (
    <div>
      <p>
        <img src={asset.url} alt={asset.alt_text} style={{ maxWidth: 160, maxHeight: 100 }} />{' '}
        <span>{asset.name}</span>
        {asset.alt_text ? <span className="muted"> — {asset.alt_text}</span> : <span className="muted"> — no alt text</span>}
      </p>
      {!readOnly && (
        <p>
          <input
            type="file"
            aria-label="Replace the file (everywhere it is used, sent emails too)"
            accept="image/jpeg,image/png,image/gif,image/webp"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) replace.mutate(file)
            }}
          />{' '}
          <span className="muted">Replace the file: everywhere it is used, sent emails too.</span>
        </p>
      )}
      {replace.error != null && <p role="alert">Not replaced: {refused(replace.error)}</p>}
    </div>
  )
}

function refused(error: unknown) {
  if (error instanceof HttpError && error.status === 403) return 'you do not have permission to change images.'
  return (error instanceof HttpError && error.detail) || 'the server refused it.'
}

/** Search the brand's images, pick one, or upload a new one. */
function Library({ onPick }: { onPick: (asset: Asset) => void }) {
  const [q, setQ] = useState('')
  const found = useAssets(q)
  const hide = useHideAsset()
  return (
    <div className="image-library">
      <TextField value={q} onChange={setQ}>
        <Label>Find an image</Label>
        <Input />
      </TextField>
      {found.data && (
        <ul className="image-library__results">
          {found.data.items.map((asset) => (
            <li key={asset.id}>
              <img src={asset.url} alt={asset.alt_text} style={{ maxWidth: 120, maxHeight: 80 }} />{' '}
              <span>{asset.name}</span>{' '}
              <Button onPress={() => onPick(asset)}>Use</Button>{' '}
              <Button onPress={() => hide.mutate(asset.id)}>Hide from the library</Button>
            </li>
          ))}
          {found.data.items.length === 0 && <li className="muted">No image matches.</li>}
        </ul>
      )}
      <Upload onUploaded={onPick} />
    </div>
  )
}

/** A new image: the file, what it shows, and its alt text. */
function Upload({ onUploaded }: { onUploaded: (asset: Asset) => void }) {
  const upload = useUploadAsset()
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [alt, setAlt] = useState('')
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (file) upload.mutate({ file, name: name.trim(), alt_text: alt.trim() }, { onSuccess: onUploaded })
      }}
    >
      <p>
        <input
          type="file"
          aria-label="Image file to upload"
          accept="image/jpeg,image/png,image/gif,image/webp"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />{' '}
        <span className="muted">JPEG, PNG, GIF or WebP, up to 5 MB.</span>
      </p>
      <TextField value={name} onChange={setName}>
        <Label>What it shows</Label>
        <Input />
        <Text slot="description" className="muted">
          The image's name is made from this, the date and its size.
        </Text>
      </TextField>
      <TextField value={alt} onChange={setAlt}>
        <Label>Alt text</Label>
        <Input />
      </TextField>
      <Button type="submit" isDisabled={upload.isPending || !file || !name.trim()}>
        {upload.isPending ? 'Uploading…' : 'Upload and use'}
      </Button>
      {upload.error != null && <p role="alert">Not uploaded: {refused(upload.error)}</p>}
    </form>
  )
}

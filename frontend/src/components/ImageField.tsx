import { useState } from 'react'
import {
  Button,
  Dialog,
  Heading,
  Input,
  Label,
  Modal,
  ModalOverlay,
  Tab,
  TabList,
  TabPanel,
  Tabs,
  Text,
  TextField,
} from 'react-aria-components'

import {
  useAsset,
  useAssets,
  useCopyAsset,
  useDescribeAsset,
  useHideAsset,
  useReplaceAsset,
  useUploadAsset,
  type Asset,
} from '../api/resources'
import { HttpError, useSession } from '../api/session'
import Choice from './Choice'
import { PAGE_SIZE } from './Pager'

/**
 * An image field: a library image, or an https address for images kept
 * elsewhere (task-112; ADR-197 point 7).
 *
 * In the form it is only the image, its name and alt text, "Change image…"
 * and "Remove". Choosing happens in a pop-in (decided with the user
 * 2026-10-15): a **Library** tab, a grid of thumbnails newest first for the
 * working brand or another brand the person holds a grant on, with a detail
 * panel to check the image before using it; and an **Upload new** tab. An
 * image from another brand is copied into this brand when used, so each
 * brand's emails depend only on its own library.
 *
 * The field stores the image's reference (`asset:<id>`), never its address.
 *
 * Alt text (ADR-197 addendum 2026-10-15, the second): a library image always
 * uses its own, changed in the library. Only a web address carries alt text
 * of its own, typed with the address and saved to the paired field (`alt`);
 * that field is never a form field of its own. `onChange` hands it back as the
 * second argument, so the caller saves both in one write.
 */
export default function ImageField({
  label,
  value,
  onChange,
  alt,
  required = false,
  readOnly = false,
  error,
}: {
  label: string
  value: string
  onChange: (value: string, alt?: string) => void
  /** The paired alt field's value, when the field has one. */
  alt?: string
  required?: boolean
  readOnly?: boolean
  error?: string
}) {
  const reference = /^asset:(\d+)$/.exec(value ?? '')
  const assetId = reference ? Number(reference[1]) : null
  const current = useAsset(assetId)
  const [open, setOpen] = useState(false)

  return (
    <div className="field image-field" role="group" aria-label={label}>
      <p className="image-field__label">
        <strong>{label}</strong>
        {required && <span className="muted"> (required)</span>}
      </p>
      <div className="image-field__current">
        {assetId != null && current.data ? (
          <>
            <img src={current.data.url} alt={current.data.alt_text} className="image-field__thumb" />
            <span>
              {current.data.name}
              <br />
              <span className="muted">{current.data.alt_text || 'No alt text'}</span>
            </span>
          </>
        ) : assetId != null && current.isError ? (
          <span role="alert">This image is not in the library any more.</span>
        ) : assetId == null && value ? (
          <>
            <img src={value} alt={alt ?? ''} className="image-field__thumb" />
            <span>
              <span className="muted">{value}</span>
              {alt !== undefined && (
                <>
                  <br />
                  <span className="muted">{alt || 'No alt text'}</span>
                </>
              )}
            </span>
          </>
        ) : (
          <span className="muted">No image.</span>
        )}
      </div>
      {!readOnly && (
        <p>
          <Button onPress={() => setOpen(true)}>{value ? 'Change image…' : 'Choose image…'}</Button>
          {value && (
            <>
              {' '}
              <Button onPress={() => onChange('')}>Remove</Button>
            </>
          )}
        </p>
      )}
      {error && (
        <p role="alert" className="field-error">
          {error}
        </p>
      )}
      <ModalOverlay isOpen={open} onOpenChange={setOpen} isDismissable className="preview-overlay">
        <Modal className="image-modal">
          <Dialog aria-label={`Choose an image: ${label}`}>
            {({ close }) => (
              <Picker
                current={value}
                alt={alt}
                onUse={(chosen, chosenAlt) => {
                  if (chosenAlt === undefined) onChange(chosen)
                  else onChange(chosen, chosenAlt)
                  close()
                }}
                onClose={close}
              />
            )}
          </Dialog>
        </Modal>
      </ModalOverlay>
    </div>
  )
}

function refused(error: unknown) {
  if (error instanceof HttpError && error.status === 403) return 'you do not have permission to change images.'
  return (error instanceof HttpError && error.detail) || 'the server refused it.'
}

/** The pop-in: the library, or a new upload, or an outside address. */
function Picker({
  current,
  alt,
  onUse,
  onClose,
}: {
  current: string
  alt?: string
  onUse: (value: string, alt?: string) => void
  onClose: () => void
}) {
  return (
    <>
      <div className="preview-head">
        <Heading slot="title">Choose an image</Heading>
        <Button onPress={onClose}>Close</Button>
      </div>
      <Tabs>
        <TabList aria-label="Where the image comes from">
          <Tab id="library">Library</Tab>
          <Tab id="upload">Upload new</Tab>
          <Tab id="address">Web address</Tab>
        </TabList>
        <TabPanel id="library">
          <Library onUse={onUse} />
        </TabPanel>
        <TabPanel id="upload">
          <Upload onUploaded={(asset) => onUse(asset.reference)} />
        </TabPanel>
        <TabPanel id="address">
          <Address
            initial={current.startsWith('asset:') ? '' : current}
            initialAlt={current.startsWith('asset:') ? undefined : alt}
            asksAlt={alt !== undefined}
            onUse={onUse}
          />
        </TabPanel>
      </Tabs>
    </>
  )
}

/** A grid of the chosen brand's images, newest first, and the one selected. */
function Library({ onUse }: { onUse: (value: string) => void }) {
  const session = useSession()
  const working = session.data?.brand?.id ?? null
  const brands = session.data?.brands ?? []
  const [brand, setBrand] = useState<number | null>(null)
  const [q, setQ] = useState('')
  const [limit, setLimit] = useState(PAGE_SIZE)
  const [selected, setSelected] = useState<Asset | null>(null)
  const shown = brand ?? working
  const found = useAssets(q, brand, limit)
  const items = found.data?.items ?? []

  return (
    <div className="image-library">
      <div className="image-library__browse">
        <div className="image-library__filters">
          {brands.length > 1 && (
            <Choice
              label="Brand"
              options={brands.map((b) => ({ id: String(b.id), name: b.name }))}
              selected={String(shown ?? '')}
              onChange={(id) => {
                setBrand(Number(id) === working ? null : Number(id))
                setSelected(null)
              }}
            />
          )}
          <TextField value={q} onChange={setQ}>
            <Label>Search (optional)</Label>
            <Input />
          </TextField>
        </div>
        <ul className="image-grid" aria-label="Images">
          {items.map((asset) => (
            <li key={asset.id}>
              <Button
                className={`image-grid__card${selected?.id === asset.id ? ' image-grid__card--selected' : ''}`}
                aria-pressed={selected?.id === asset.id}
                onPress={() => setSelected(asset)}
              >
                <img src={asset.url} alt="" />
                <span className="image-grid__name">{asset.label}</span>
                <span className="muted">
                  {asset.width}×{asset.height}
                </span>
              </Button>
            </li>
          ))}
        </ul>
        {found.data && items.length === 0 && <p className="muted">No image here yet.</p>}
        {found.data && found.data.total > items.length && (
          <Button onPress={() => setLimit(limit + PAGE_SIZE)}>Load more</Button>
        )}
      </div>
      <aside className="image-library__detail" aria-label="Selected image">
        {selected ? (
          <Detail
            key={selected.id}
            asset={selected}
            foreign={shown !== working}
            brandName={brands.find((b) => b.id === shown)?.name ?? ''}
            workingName={brands.find((b) => b.id === working)?.name ?? 'this brand'}
            onUse={onUse}
            onHidden={() => setSelected(null)}
          />
        ) : (
          <p className="muted">Select an image to see it larger and use it.</p>
        )}
      </aside>
    </div>
  )
}

/** One image, larger, with its facts and what can be done with it. */
function Detail({
  asset,
  foreign,
  brandName,
  workingName,
  onUse,
  onHidden,
}: {
  asset: Asset
  foreign: boolean
  brandName: string
  workingName: string
  onUse: (value: string) => void
  onHidden: () => void
}) {
  const copy = useCopyAsset()
  const describe = useDescribeAsset()
  const replace = useReplaceAsset(asset.id)
  const hide = useHideAsset()
  const [alt, setAlt] = useState(asset.alt_text)
  return (
    <div>
      <img src={asset.url} alt={asset.alt_text} className="image-library__preview" />
      <dl className="facts">
        <dt>Name</dt>
        <dd>{asset.name}</dd>
        <dt>Size</dt>
        <dd>
          {asset.width}×{asset.height} px, {Math.max(1, Math.round(asset.size_bytes / 1024))} KB
        </dd>
        {brandName && (
          <>
            <dt>Brand</dt>
            <dd>{brandName}</dd>
          </>
        )}
      </dl>
      {foreign ? (
        <Button
          onPress={() => copy.mutate(asset.id, { onSuccess: (made) => onUse(made.reference) })}
          isDisabled={copy.isPending}
        >
          {copy.isPending ? 'Copying…' : `Copy into ${workingName} and use`}
        </Button>
      ) : (
        <Button onPress={() => onUse(asset.reference)}>Use this image</Button>
      )}
      {copy.error != null && <p role="alert">Not copied: {refused(copy.error)}</p>}
      {!foreign && (
        <details className="image-library__more">
          <summary>More: alt text, replace, hide</summary>
          <TextField value={alt} onChange={setAlt}>
            <Label>Alt text</Label>
            <Input />
            <Text slot="description" className="muted">
              Used wherever this image is placed, in every email.
            </Text>
          </TextField>
          <Button onPress={() => describe.mutate({ id: asset.id, alt_text: alt })} isDisabled={alt === asset.alt_text}>
            Save alt text
          </Button>
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
          <Button onPress={() => hide.mutate(asset.id, { onSuccess: onHidden })}>Hide from the library</Button>
          {(describe.error ?? replace.error ?? hide.error) != null && (
            <p role="alert">Not changed: {refused(describe.error ?? replace.error ?? hide.error)}</p>
          )}
        </details>
      )}
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
      className="image-upload"
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
          The image's name is made from this, the brand, the date and its size.
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

/** An outside address, for images that live in a DAM or CDN, with its alt
 * text when the field keeps one: an address has no library entry to hold it. */
function Address({
  initial,
  initialAlt,
  asksAlt,
  onUse,
}: {
  initial: string
  initialAlt?: string
  asksAlt: boolean
  onUse: (value: string, alt?: string) => void
}) {
  const [address, setAddress] = useState(initial)
  const [alt, setAlt] = useState(initialAlt ?? '')
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (asksAlt) onUse(address.trim(), alt.trim())
        else onUse(address.trim())
      }}
    >
      <TextField value={address} onChange={setAddress} type="url">
        <Label>Image address</Label>
        <Input />
        <Text slot="description" className="muted">
          A full address starting with https://, for images kept elsewhere.
        </Text>
      </TextField>
      {asksAlt && (
        <TextField value={alt} onChange={setAlt}>
          <Label>Alt text</Label>
          <Input />
          <Text slot="description" className="muted">
            What the image shows, for people who cannot see it.
          </Text>
        </TextField>
      )}
      <Button type="submit" isDisabled={!address.trim()}>
        Use this address
      </Button>
    </form>
  )
}

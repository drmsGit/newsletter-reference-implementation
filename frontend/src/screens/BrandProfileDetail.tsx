import { useState, type FormEvent } from 'react'
import { Button, Input, Label, Text, TextArea, TextField } from 'react-aria-components'
import { Link, useNavigate, useParams } from 'react-router'

import {
  useBrandProfile,
  useBrandProfileStructure,
  useDeleteBrandProfile,
  useDuplicateBrandProfile,
  useMakeDefaultBrandProfile,
  useSaveBrandProfile,
  type BrandProfile,
  type ProfileField,
} from '../api/resources'
import { HttpError } from '../api/session'
import { SaveState, fieldError } from '../components/EditorFields'
import ScreenState from '../components/ScreenState'
import { fieldLabels } from './BrandProfiles'

/**
 * One brand profile (task-350; ADR-194). The form is built from the setup
 * file's fields, grouped as it groups them, so an installation that declares
 * four font sizes gets four fields and this file names none.
 *
 * **Saved with a button, not field by field** like the variant editor: a
 * profile is a set of values that belong together (a colour and the text on
 * it, an address and its company), and half of a change applied to every
 * email using the profile is worse than none. The save states the version it
 * was read at (If-Match), so it never overwrites somebody else's newer one.
 */
export default function BrandProfileDetail() {
  const id = Number(useParams().id)
  const profile = useBrandProfile(id)
  const structure = useBrandProfileStructure()
  // Here rather than in the form: the form remounts on every new version, and
  // the save's outcome ("Saved.", a refusal) must outlive that.
  const save = useSaveBrandProfile(id)

  return (
    <>
      <p>
        <Link to="/brand-profiles">← Brand profiles</Link>
      </p>
      <ScreenState query={profile}>
        <ScreenState query={structure}>
          {profile.data && structure.data && (
            // Keyed on the version: a save or a reload starts the form from what is stored.
            <ProfileForm
              key={profile.data.updated_at}
              profile={profile.data}
              fields={structure.data}
              save={save}
              reload={() => profile.refetch()}
            />
          )}
        </ScreenState>
      </ScreenState>
    </>
  )
}

function asText(value: unknown): string {
  return value === null || value === undefined ? '' : String(value)
}

function ProfileForm({
  profile,
  fields,
  save,
  reload,
}: {
  profile: BrandProfile
  fields: ProfileField[]
  save: ReturnType<typeof useSaveBrandProfile>
  reload: () => void
}) {
  const readOnly = !profile.may_manage
  const [name, setName] = useState(profile.name)
  const [language, setLanguage] = useState(profile.language)
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((f) => [f.name, asText(profile.field_values[f.name])])),
  )
  const dirty =
    name !== profile.name ||
    language !== profile.language ||
    fields.some((f) => values[f.name] !== asText(profile.field_values[f.name]))

  function submit(event: FormEvent) {
    event.preventDefault()
    if (!dirty || save.isPending || readOnly) return
    // Every field goes with the save: the PUT replaces the values, and an
    // empty one is dropped by the server, which is how a value is cleared.
    save.mutate({ name: name.trim(), language: language.trim(), field_values: values })
  }

  const groups = [...new Set(fields.map((f) => f.group))]

  return (
    // noValidate: the server's per-field refusals are the rules, in its words;
    // the browser's own URL check would refuse first, in different ones.
    <form onSubmit={submit} aria-labelledby="profile-heading" noValidate>
      <h1 id="profile-heading">{profile.name}</h1>
      <p className="muted">
        {profile.is_default ? 'Default profile · ' : ''}
        {profile.kind} · {profile.language}
      </p>
      {readOnly && (
        <p className="muted">You can read this profile. Changing it needs the brand-profile permission.</p>
      )}
      {profile.missing.length > 0 && (
        <p role="status">
          Incomplete. An email cannot use this profile until these are filled:{' '}
          {fieldLabels(profile.missing, fields)}.
        </p>
      )}

      <fieldset>
        <legend>Profile</legend>
        <TextField value={name} onChange={setName} isRequired isReadOnly={readOnly} isInvalid={!!fieldError(save.error, 'name')}>
          <Label>Name</Label>
          <Input />
          <FieldError message={fieldError(save.error, 'name')} />
        </TextField>
        <TextField
          value={language}
          onChange={setLanguage}
          isRequired
          isReadOnly={readOnly}
          isInvalid={!!fieldError(save.error, 'language')}
        >
          <Label>Language</Label>
          <Input />
          <Text slot="description" className="muted">
            The language its texts are in, such as en or de. One profile per language.
          </Text>
          <FieldError message={fieldError(save.error, 'language')} />
        </TextField>
      </fieldset>

      {groups.map((group) => (
        <fieldset key={group}>
          <legend>{group}</legend>
          {fields
            .filter((f) => f.group === group)
            .map((field) => (
              <ProfileInput
                key={field.name}
                field={field}
                value={values[field.name] ?? ''}
                onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))}
                required={field.required_for.includes(profile.kind)}
                readOnly={readOnly}
                error={fieldError(save.error, field.name)}
              />
            ))}
        </fieldset>
      ))}

      {!readOnly && (
        <p>
          <Button type="submit" isDisabled={!dirty || save.isPending}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>
          {!dirty && save.isSuccess && <span className="muted"> Saved.</span>}
        </p>
      )}
      <SaveState mutation={save} reload={reload} what="this profile" />
      {!readOnly && <ProfileActions profile={profile} dirty={dirty} />}
    </form>
  )
}

/** What each field type expects, said where it is typed. */
const HINTS: Record<string, string> = {
  colour: 'A colour as #rgb or #rrggbb, for example #1a5db0.',
  size: 'With its unit, for example 16px.',
  url: 'A full address starting with https://.',
  image: 'The full address of the image, starting with https://.',
  font_family: 'A font list with a safe fallback, for example Georgia, serif.',
}

function ProfileInput({
  field,
  value,
  onChange,
  required,
  readOnly,
  error,
}: {
  field: ProfileField
  value: string
  onChange: (value: string) => void
  required: boolean
  readOnly: boolean
  error: string | undefined
}) {
  return (
    <TextField
      className="react-aria-TextField field"
      value={value}
      onChange={onChange}
      isReadOnly={readOnly}
      isInvalid={!!error}
    >
      <Label>
        {field.label}
        {required && <span className="muted"> (required to send)</span>}
      </Label>
      {field.multiline ? (
        <TextArea rows={3} />
      ) : (
        <Input type={field.type === 'url' || field.type === 'image' ? 'url' : field.type === 'number' ? 'number' : 'text'} />
      )}
      {HINTS[field.type] && (
        <Text slot="description" className="muted">
          {HINTS[field.type]}
        </Text>
      )}
      <FieldError message={error} />
    </TextField>
  )
}

function FieldError({ message }: { message: string | undefined }) {
  return message ? (
    <p role="alert" className="field-error">
      {message}
    </p>
  ) : null
}

/** Duplicate, make default, delete. The default can be changed but never deleted (ADR-194 point 1). */
function ProfileActions({ profile, dirty }: { profile: BrandProfile; dirty: boolean }) {
  const navigate = useNavigate()
  const duplicate = useDuplicateBrandProfile(profile.id)
  const makeDefault = useMakeDefaultBrandProfile(profile.id)
  const remove = useDeleteBrandProfile(profile.id)
  const [confirming, setConfirming] = useState(false)
  const busy = duplicate.isPending || makeDefault.isPending || remove.isPending
  const failed = [duplicate, makeDefault, remove].find((m) => m.isError)

  return (
    <section aria-label="Profile actions" className="actions">
      {dirty && <p className="muted">Save or undo your changes first; these act on the stored profile.</p>}
      <Button
        isDisabled={busy || dirty}
        onPress={() => duplicate.mutate(undefined, { onSuccess: (copy) => navigate(`/brand-profiles/${copy.id}`) })}
      >
        Duplicate
      </Button>{' '}
      {!profile.is_default && (
        <>
          <Button isDisabled={busy || dirty} onPress={() => makeDefault.mutate()}>
            Make default
          </Button>{' '}
          {confirming ? (
            <span role="group" aria-label="Confirm delete">
              Variants using it will move to the default profile.{' '}
              <Button
                isDisabled={busy}
                onPress={() => remove.mutate(undefined, { onSuccess: () => navigate('/brand-profiles') })}
              >
                Delete {profile.name}
              </Button>{' '}
              <Button onPress={() => setConfirming(false)}>Keep it</Button>
            </span>
          ) : (
            <Button isDisabled={busy || dirty} onPress={() => setConfirming(true)}>
              Delete…
            </Button>
          )}
        </>
      )}
      {failed && (
        <p role="alert">
          {failed.error instanceof HttpError && failed.error.status === 403
            ? 'You do not have permission to manage brand profiles in this brand.'
            : `Not done: ${(failed.error instanceof HttpError && failed.error.detail) || 'the server refused it.'}`}
        </p>
      )}
    </section>
  )
}

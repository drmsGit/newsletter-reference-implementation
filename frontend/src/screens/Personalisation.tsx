import { useState, type FormEvent } from 'react'
import { Button, Input, Label, TextField } from 'react-aria-components'
import { useNavigate, useParams } from 'react-router'

import {
  useCreateExpression,
  useDeleteExpression,
  useExpressions,
  useSaveExpression,
  type ExpressionCase,
  type ExpressionEntry,
  type ExpressionLanguage,
} from '../api/resources'
import { HttpError } from '../api/session'
import Choice from '../components/Choice'
import DataTable, { type DataColumn } from '../components/DataTable'
import ScreenState from '../components/ScreenState'

/** A part of Settings, beside the brand profiles whose texts it completes. */
export const PERSONALISATION = '/settings/personalisation'

const FIELDS = [
  { id: 'gender', name: 'Gender' },
  { id: 'first_name', name: 'First name' },
  { id: 'last_name', name: 'Last name' },
]
const TESTS = [
  { id: 'filled', name: 'is filled' },
  { id: 'empty', name: 'is empty' },
  { id: 'equals', name: 'is' },
]
const GENDERS = [
  { id: 'female', name: 'female' },
  { id: 'male', name: 'male' },
  { id: 'diverse', name: 'diverse' },
]

const COLUMNS: DataColumn<ExpressionEntry>[] = [
  { key: 'label', header: 'Entry', isRowHeader: true, render: (e) => e.label },
  { key: 'name', header: 'In a text', render: (e) => `{{${e.name}}}` },
  { key: 'languages', header: 'Languages', render: (e) => Object.keys(e.languages).sort().join(', ') },
]

/**
 * The brand's expression dictionary (task-365; ADR-199): entries a text can
 * use, such as {{salutation_formal}}. Each says, per language, what to write
 * for which recipient, and what to write when nothing fits.
 */
export default function Personalisation() {
  const dictionary = useExpressions()
  const navigate = useNavigate()
  return (
    <>
      <h1>Personalisation</h1>
      <p className="muted">
        Entries a text can use, such as a salutation. Each one says, per language, what to write for which
        recipient, and what to write when nothing is known about them. An email uses its brand profile's
        language.
      </p>
      <ScreenState query={dictionary}>
        {dictionary.data && (
          <>
            {dictionary.data.may_manage && <NewEntry />}
            <DataTable
              label="Entries"
              columns={COLUMNS}
              items={dictionary.data.items}
              emptyMessage="This brand has no entries yet."
              onRowAction={(e) => navigate(`${PERSONALISATION}/${e.id}`)}
            />
          </>
        )}
      </ScreenState>
    </>
  )
}

function problem(error: unknown): string {
  if (error instanceof HttpError && error.status === 403) return 'you do not have permission to change these.'
  return (error instanceof HttpError && error.detail) || 'the server refused it.'
}

/** A name, a label and a first language; the cases are added on the entry's page. */
function NewEntry() {
  const create = useCreateExpression()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [label, setLabel] = useState('')
  const [language, setLanguage] = useState('de')
  const [fallback, setFallback] = useState('')

  function submit(event: FormEvent) {
    event.preventDefault()
    create.mutate(
      { name: name.trim(), label: label.trim(), languages: { [language.trim()]: { cases: [], fallback } } },
      { onSuccess: (entry) => navigate(`${PERSONALISATION}/${entry.id}`) },
    )
  }

  return (
    <details className="new-entry">
      <summary>New entry</summary>
      <form onSubmit={submit}>
        <TextField value={name} onChange={setName} isRequired>
          <Label>Name in a text, fixed once created (letters, digits, _)</Label>
          <Input />
        </TextField>
        <TextField value={label} onChange={setLabel} isRequired>
          <Label>Label</Label>
          <Input />
        </TextField>
        <TextField value={language} onChange={setLanguage} isRequired>
          <Label>First language (de, en, …)</Label>
          <Input />
        </TextField>
        <TextField value={fallback} onChange={setFallback} isRequired>
          <Label>Text when nothing is known about the recipient</Label>
          <Input />
        </TextField>
        <Button type="submit" isDisabled={create.isPending || !name.trim() || !label.trim() || !fallback.trim()}>
          Create
        </Button>
        {create.error != null && <p role="alert">Not created: {problem(create.error)}</p>}
      </form>
    </details>
  )
}

/** One entry: its label, and per language its cases and fallback. */
export function PersonalisationEntry() {
  const { id } = useParams()
  const dictionary = useExpressions()
  const entry = dictionary.data?.items.find((e) => e.id === Number(id))
  return (
    <ScreenState query={dictionary}>
      {dictionary.data &&
        (entry ? (
          <EntryForm key={entry.updated_at} entry={entry} readOnly={!dictionary.data.may_manage} />
        ) : (
          <p role="alert">This entry is not in the brand's dictionary.</p>
        ))}
    </ScreenState>
  )
}

function EntryForm({ entry, readOnly }: { entry: ExpressionEntry; readOnly: boolean }) {
  const save = useSaveExpression(entry.id)
  const remove = useDeleteExpression(entry.id)
  const navigate = useNavigate()
  const [label, setLabel] = useState(entry.label)
  const [languages, setLanguages] = useState<Record<string, ExpressionLanguage>>(entry.languages)
  const [added, setAdded] = useState('')
  const [confirm, setConfirm] = useState(false)

  const setLanguage = (code: string, spec: ExpressionLanguage) => setLanguages({ ...languages, [code]: spec })

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        save.mutate({ version: entry.updated_at, label, languages })
      }}
    >
      <h1>{entry.label}</h1>
      <p className="muted">
        In a text: <code>{`{{${entry.name}}}`}</code>. The name stays as it is; a different name is a new entry.
      </p>
      <TextField value={label} onChange={setLabel} isReadOnly={readOnly}>
        <Label>Label</Label>
        <Input />
      </TextField>
      {Object.keys(languages)
        .sort()
        .map((code) => (
          <LanguageCases
            key={code}
            code={code}
            spec={languages[code]}
            readOnly={readOnly}
            onChange={(spec) => setLanguage(code, spec)}
            onRemove={() => {
              const rest = { ...languages }
              delete rest[code]
              setLanguages(rest)
            }}
          />
        ))}
      {!readOnly && (
        <p>
          <TextField value={added} onChange={setAdded}>
            <Label>Add a language (de, en, en-GB, …)</Label>
            <Input />
          </TextField>
          <Button
            isDisabled={!added.trim() || added.trim() in languages}
            onPress={() => {
              setLanguage(added.trim(), { cases: [], fallback: '' })
              setAdded('')
            }}
          >
            Add language
          </Button>
        </p>
      )}
      {!readOnly && (
        <p>
          <Button type="submit" isDisabled={save.isPending}>
            {save.isPending ? 'Saving…' : 'Save'}
          </Button>{' '}
          {confirm ? (
            <span role="group" aria-label={`Delete ${entry.label}?`}>
              <Button onPress={() => remove.mutate(entry.updated_at, { onSuccess: () => navigate(PERSONALISATION) })}>
                Delete {entry.label}
              </Button>{' '}
              <Button onPress={() => setConfirm(false)}>Keep it</Button>
            </span>
          ) : (
            <Button onPress={() => setConfirm(true)}>Delete…</Button>
          )}
        </p>
      )}
      {save.isSuccess && <p role="status">Saved.</p>}
      {save.error != null && <p role="alert">Not saved: {problem(save.error)}</p>}
      {remove.error != null && <p role="alert">Not deleted: {problem(remove.error)}</p>}
    </form>
  )
}

/** One language: the cases in order, the first that fits wins, then the fallback. */
function LanguageCases({
  code,
  spec,
  readOnly,
  onChange,
  onRemove,
}: {
  code: string
  spec: ExpressionLanguage
  readOnly: boolean
  onChange: (spec: ExpressionLanguage) => void
  onRemove: () => void
}) {
  const cases = spec.cases ?? []
  const setCase = (index: number, next: ExpressionCase) =>
    onChange({ ...spec, cases: cases.map((c, i) => (i === index ? next : c)) })
  return (
    <fieldset className="language-cases">
      <legend>{code}</legend>
      <p className="muted">
        Tried in order; the first that fits is used. A case only fits when every name its text uses is filled.
        Texts may use {'{{first_name}}'} and {'{{last_name}}'}.
      </p>
      <ol>
        {cases.map((c, index) => (
          <li key={index} role="group" aria-label={`${code} case ${index + 1}`}>
            <Choice
              label="When"
              options={FIELDS}
              selected={c.field}
              onChange={(field) => setCase(index, { ...c, field })}
            />
            <Choice
              label="Test"
              options={TESTS}
              selected={c.is}
              onChange={(test) =>
                setCase(index, test === 'equals' ? { ...c, is: test } : { ...c, is: test, value: undefined })
              }
            />
            {c.is === 'equals' &&
              (c.field === 'gender' ? (
                <Choice
                  label="Value"
                  options={GENDERS}
                  selected={c.value ?? ''}
                  onChange={(value) => setCase(index, { ...c, value })}
                />
              ) : (
                <TextField value={c.value ?? ''} onChange={(value) => setCase(index, { ...c, value })} isReadOnly={readOnly}>
                  <Label>Value</Label>
                  <Input />
                </TextField>
              ))}
            <TextField value={c.text} onChange={(text) => setCase(index, { ...c, text })} isReadOnly={readOnly}>
              <Label>Write</Label>
              <Input />
            </TextField>
            {!readOnly && (
              <Button onPress={() => onChange({ ...spec, cases: cases.filter((_, i) => i !== index) })}>
                Remove case
              </Button>
            )}
          </li>
        ))}
      </ol>
      {!readOnly && (
        <Button
          onPress={() => onChange({ ...spec, cases: [...cases, { field: 'first_name', is: 'filled', text: '' }] })}
        >
          Add a case
        </Button>
      )}
      <TextField value={spec.fallback} onChange={(fallback) => onChange({ ...spec, fallback })} isReadOnly={readOnly}>
        <Label>Otherwise write ({code})</Label>
        <Input />
      </TextField>
      {!readOnly && <Button onPress={onRemove}>Remove {code}</Button>}
    </fieldset>
  )
}

import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import {
  useRetranslate,
  useRetranslations,
  useSaveContentRecord,
  useTranslateContent,
  type ContentRecordDetail,
} from '../api/resources'
import { HttpError } from '../api/session'
import type { components } from '../api/schema'
import AIButton from '../components/AIButton'
import Choice from '../components/Choice'
import { Proposal } from './ContentDraft'

type ContentField = components['schemas']['ContentField']

const NOT_SET = ''

/** "de" as "German", in the client's language; a code it does not know as itself. */
export function languageName(code: string | null | undefined): string {
  if (!code) return 'not set'
  try {
    return new Intl.DisplayNames(['en'], { type: 'language' }).of(code) ?? code
  } catch {
    return code
  }
}

/**
 * A record's language (ADR-200 point 1): one of its brand's profile
 * languages, or not set. Shown as text with the reason while the record is
 * linked, when it may not change.
 */
export function LanguageChoice({ record }: { record: ContentRecordDetail }) {
  const save = useSaveContentRecord(record.id)
  if (record.language_locked)
    return (
      <dl className="facts">
        <dt>Language</dt>
        <dd>
          {languageName(record.language)} <span className="muted">— {record.language_locked}</span>
        </dd>
      </dl>
    )
  const options = [
    { id: NOT_SET, name: 'Not set (any language)' },
    ...(record.language_choices ?? []).map((code) => ({ id: code, name: languageName(code) })),
  ]
  return (
    <>
      <Choice
        label="Language"
        options={options}
        selected={record.language ?? NOT_SET}
        onChange={(next) => save.mutate({ language: next === NOT_SET ? null : next })}
      />
      {save.error && (
        <p role="alert">
          {(save.error instanceof HttpError && save.error.detail) ||
            'The language was not saved.'}
        </p>
      )}
    </>
  )
}

/**
 * Translations (task-369; ADR-200 points 3-5). On an original: its
 * translations, and translating into another of the brand's languages, which
 * makes a new record and opens it. On a translation: where it came from, and
 * when the original's text changed since, a fresh translation to take field
 * by field.
 */
export default function Translations({ record, fields }: { record: ContentRecordDetail; fields: ContentField[] }) {
  return (
    <section aria-labelledby="translations-heading">
      <h2 id="translations-heading">Translations</h2>
      {record.original ? <OfAnOriginal record={record} fields={fields} /> : <AnOriginal record={record} />}
    </section>
  )
}

function AnOriginal({ record }: { record: ContentRecordDetail }) {
  const translate = useTranslateContent(record.id)
  const navigate = useNavigate()
  const translations = record.translations ?? []
  const taken = new Set([record.language, ...translations.map((t) => t.language)])
  const targets = (record.language_choices ?? []).filter((code) => !taken.has(code))
  const [target, setTarget] = useState('')
  const chosen = targets.includes(target) ? target : (targets[0] ?? '')
  const refused = translate.error instanceof HttpError ? translate.error : null

  return (
    <>
      {translations.length > 0 && (
        <ul aria-label="Translations of this record">
          {translations.map((t) => (
            <li key={t.id}>
              {languageName(t.language)}: <Link to={`/content/${t.id}`}>{t.title}</Link>
            </li>
          ))}
        </ul>
      )}
      {!record.language ? (
        <p className="muted">Set this record&apos;s language above to translate it.</p>
      ) : targets.length === 0 ? (
        <p className="muted">
          It is translated into every language of the brand&apos;s profiles. A new language starts with a brand
          profile in it.
        </p>
      ) : (
        <div className="inline-form">
          <Choice
            label="Translate into"
            options={targets.map((code) => ({ id: code, name: languageName(code) }))}
            selected={chosen}
            onChange={setTarget}
          />
          <AIButton
            pending={translate.isPending}
            onPress={() =>
              translate.mutate(chosen, { onSuccess: (made) => navigate(`/content/${made.record_id}`) })
            }
          >
            Translate with AI
          </AIButton>
        </div>
      )}
      {translate.error && (
        <p role="alert">
          {refused?.detail || 'The translation could not be made.'}
        </p>
      )}
    </>
  )
}

function OfAnOriginal({ record, fields }: { record: ContentRecordDetail; fields: ContentField[] }) {
  const changed = record.original_changed ?? []
  const retranslate = useRetranslate(record.id)
  const proposals = useRetranslations(record.id, changed.length > 0)
  const labels: Record<string, string> = {
    title: 'Title',
    description: 'Description',
    ...Object.fromEntries(fields.map((f) => [f.name, f.label ?? f.name])),
  }
  const latest = proposals.data?.[0]
  const original = record.original!

  return (
    <>
      <p>
        {languageName(record.language)}, translated by AI from{' '}
        <Link to={`/content/${original.id}`}>{original.title}</Link> ({languageName(original.language)})
        {record.latest_version_number == null && ' — review it before publishing'}.
      </p>
      {changed.length === 0 ? (
        <p className="muted">Up to date with the original.</p>
      ) : (
        <>
          <p role="status">
            The original changed since this was translated: {changed.map((name) => labels[name] ?? name).join(', ')}.
          </p>
          <AIButton pending={retranslate.isPending} onPress={() => retranslate.mutate()}>
            Translate again
          </AIButton>
          {retranslate.error && (
            <p role="alert">
              {(retranslate.error instanceof HttpError && retranslate.error.detail) ||
                'The translation could not be asked for.'}
            </p>
          )}
          {latest && <Proposal key={latest.run_id} recordId={record.id} draft={latest} ticked={changed} />}
        </>
      )}
    </>
  )
}

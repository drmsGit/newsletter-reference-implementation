import { useState, type ReactNode } from 'react'
import {
  Button,
  Input,
  Label,
  ListBox,
  ListBoxItem,
  Popover,
  Select,
  SelectValue,
  TextArea,
  TextField,
} from 'react-aria-components'

import {
  usePublishPrompt,
  useSaveAiProvider,
  useSaveSignals,
  useSaveSendCap,
  useSaveSpendCap,
  useSetTaskApproval,
  useSetTaskModel,
  useSettings,
  type SettingsView,
} from '../api/resources'
import { HttpError } from '../api/session'
import DataTable from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/**
 * Settings.
 *
 * **Who may change what is the server's answer.** `may_manage` and
 * `may_configure_ai` come with the settings themselves, computed by the same
 * rules the write routes apply: a person -- never a machine -- holding
 * `settings.manage`, plus `ai.run` for a task's model. Without them the screen
 * is the read-only view; with them, each value gets its own control. This
 * screen never decides that for itself.
 *
 * **Each change is saved on purpose**, with its own button: these values decide
 * how many people one send may reach and how much AI may spend, and a control
 * that saved as you typed would make an accident one keystroke long. No setting
 * is approvable (ADR-142's addendum) and every change is audited (task-245).
 *
 * Channels and delivery providers are shown, not edited: there is no write
 * route for either.
 */
export default function Settings() {
  const settings = useSettings()

  return (
    <>
      <h1>Settings</h1>
      <ScreenState query={settings}>
        {settings.data && (
          <>
            <p className="muted">
              {settings.data.may_manage
                ? 'Changes take effect for the whole deployment, and each one is recorded in the audit log.'
                : 'Read-only: changing settings needs permission to manage them. Every change is recorded in the audit log.'}
            </p>
            <Sections s={settings.data} />
          </>
        )}
      </ScreenState>
    </>
  )
}

/** What a save did, said once beside its control. */
function Outcome({ write }: { write: { isSuccess: boolean; isError: boolean; error: unknown } }) {
  if (write.isSuccess) return <p role="status">Saved.</p>
  if (!write.isError) return null
  const error = write.error instanceof HttpError ? write.error : undefined
  return (
    <p role="alert">
      {error?.status === 403
        ? 'You do not have permission to change this.'
        : error?.detail
          ? `Not saved: ${error.detail}`
          : 'Not saved. The server refused the value.'}
    </p>
  )
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <TextField value={value} onChange={onChange} inputMode="decimal">
      <Label>{label}</Label>
      <Input />
    </TextField>
  )
}

function Choice({
  label,
  options,
  selected,
  onChange,
}: {
  label: string
  options: { id: string; name: string }[]
  selected: string
  onChange: (id: string) => void
}) {
  return (
    <Select selectedKey={selected} onSelectionChange={(key) => onChange(String(key))}>
      <Label>{label}</Label>
      <Button>
        <SelectValue />
      </Button>
      <Popover>
        <ListBox items={options}>{(item) => <ListBoxItem id={item.id}>{item.name}</ListBoxItem>}</ListBox>
      </Popover>
    </Select>
  )
}

function Form({ children, onSave, saving, label }: {
  children: ReactNode
  onSave: () => void
  saving: boolean
  label: string
}) {
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        onSave()
      }}
    >
      {children}
      <Button type="submit" isDisabled={saving}>
        {saving ? 'Saving…' : label}
      </Button>
    </form>
  )
}

/** Whole numbers only; anything else is not sent at all. What a value may BE
 * (positive, warn not above hard stop) is the server's rule, not this one. */
function parseWhole(raw: string): number | null {
  const trimmed = raw.trim()
  return /^\d+$/.test(trimmed) ? Number(trimmed) : null
}

function SendCap({ s }: { s: SettingsView }) {
  const save = useSaveSendCap()
  const [value, setValue] = useState(String(s.max_send_recipients))
  const [invalid, setInvalid] = useState(false)
  if (!s.may_manage) {
    return (
      <dl className="facts">
        <dt>Most recipients one send may reach</dt>
        <dd>{s.max_send_recipients}</dd>
      </dl>
    )
  }
  return (
    <Form
      label="Save send cap"
      saving={save.isPending}
      onSave={() => {
        const cap = parseWhole(value)
        setInvalid(cap === null)
        if (cap !== null) save.mutate(cap)
      }}
    >
      <NumberField label="Most recipients one send may reach" value={value} onChange={setValue} />
      {invalid && <p role="alert">Enter a whole number.</p>}
      <Outcome write={save} />
    </Form>
  )
}

function SpendCap({ s }: { s: SettingsView }) {
  const save = useSaveSpendCap()
  const cap = s.ai_budget.cap
  const [warn, setWarn] = useState(String(cap.warn_tokens))
  const [stop, setStop] = useState(String(cap.hard_stop_tokens))
  const [usd, setUsd] = useState(String(cap.budget_usd))
  const [invalid, setInvalid] = useState(false)
  if (!s.may_manage) return null
  return (
    <Form
      label="Save AI budget"
      saving={save.isPending}
      onSave={() => {
        const warnTokens = parseWhole(warn)
        const stopTokens = parseWhole(stop)
        const budget = Number(usd.trim().replace(',', '.'))
        const ok = warnTokens !== null && stopTokens !== null && usd.trim() !== '' && !Number.isNaN(budget)
        setInvalid(!ok)
        if (ok) save.mutate({ warn_tokens: warnTokens, hard_stop_tokens: stopTokens, budget_usd: budget })
      }}
    >
      <NumberField label="Warn at (tokens)" value={warn} onChange={setWarn} />
      <NumberField label="Stop at (tokens)" value={stop} onChange={setStop} />
      <NumberField label="Budget (USD)" value={usd} onChange={setUsd} />
      {invalid && <p role="alert">Tokens are whole numbers; the budget is a number.</p>}
      <Outcome write={save} />
    </Form>
  )
}

function Provider({ s }: { s: SettingsView }) {
  const save = useSaveAiProvider()
  const [provider, setProvider] = useState(s.ai_provider)
  if (!s.may_manage) {
    return (
      <dl className="facts">
        <dt>Provider</dt>
        <dd>{s.ai_provider}</dd>
      </dl>
    )
  }
  return (
    <Form label="Save provider" saving={save.isPending} onSave={() => save.mutate(provider)}>
      <Choice
        label="AI provider"
        options={s.ai_providers.map((p) => ({ id: p, name: p }))}
        selected={provider}
        onChange={setProvider}
      />
      <Outcome write={save} />
    </Form>
  )
}

const DEFAULT_MODEL = '__default__'

function Task({ s, task }: { s: SettingsView; task: SettingsView['ai_tasks'][number] }) {
  const approval = useSetTaskApproval()
  const model = useSetTaskModel()
  const [mode, setMode] = useState(task.approval_mode)
  const [chosen, setChosen] = useState(task.model ?? DEFAULT_MODEL)

  return (
    <section aria-labelledby={`task-${task.key}`}>
      <h3 id={`task-${task.key}`}>{task.label}</h3>
      <p>{task.description}</p>

      {s.may_configure_ai ? (
        <Form
          label="Save model"
          saving={model.isPending}
          onSave={() => model.mutate({ task: task.key, model: chosen === DEFAULT_MODEL ? null : chosen })}
        >
          <Choice
            label={`Model for ${task.label}`}
            options={[
              { id: DEFAULT_MODEL, name: `the default (${s.ai_model})` },
              ...s.governed_models.map((m) => ({ id: m, name: m })),
            ]}
            selected={chosen}
            onChange={setChosen}
          />
          <Outcome write={model} />
        </Form>
      ) : (
        <dl className="facts">
          <dt>Model</dt>
          <dd>{task.model ?? `the default (${s.ai_model})`}</dd>
        </dl>
      )}

      {s.may_manage ? (
        <Form
          label="Save output mode"
          saving={approval.isPending}
          onSave={() =>
            approval.mutate({ task: task.key, mode: mode as 'auto_apply' | 'require_approval' })
          }
        >
          <Choice
            label={`Output of ${task.label}`}
            options={[
              // The service's own words for the two modes (settings.service).
              { id: 'auto_apply', name: 'applied directly' },
              { id: 'require_approval', name: 'held for review' },
            ]}
            selected={mode}
            onChange={setMode}
          />
          <Outcome write={approval} />
        </Form>
      ) : (
        <dl className="facts">
          <dt>Output</dt>
          <dd>{task.approval_mode === 'require_approval' ? 'held for review' : 'applied directly'}</dd>
        </dl>
      )}

      <dl className="facts">
        <dt>Prompt</dt>
        <dd>
          {task.prompt_version != null
            ? `version ${task.prompt_version} of ${task.versions.length}`
            : 'the built-in default (never published)'}
        </dd>
      </dl>
      {s.may_configure_ai && <PromptEditor task={task} />}
      <details>
        <summary>The live prompt</summary>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{task.prompt_body}</pre>
        {task.versions.length > 0 && (
          <p className="muted">
            Published versions:{' '}
            {task.versions.map((v) => `v${v.version} (${formatDate(v.created_at)})`).join(', ')}
          </p>
        )}
      </details>
    </section>
  )
}

/** A decimal number, comma or point; negative allowed (an unsubscribe weighs
 * against). Blank is not a number here -- it means "the default". */
function parseNumber(raw: string): number | null {
  const trimmed = raw.trim().replace(',', '.')
  return trimmed !== '' && !Number.isNaN(Number(trimmed)) ? Number(trimmed) : null
}

/**
 * Weights and half-lives, one row per contribution type (ADR-132).
 *
 * **A blank field means the code default**, and each field says what that is:
 * the save replaces the whole table, so a type left out falls back. The server
 * stores only values that differ from the default, so saving the table
 * unchanged pins nothing. Whether a half-life is valid (more than 0 days) is
 * the server's rule, and its reason is shown when it refuses one.
 */
function SignalsEditor({ s }: { s: SettingsView }) {
  const save = useSaveSignals()
  const types = s.known_contribution_types
  const [weights, setWeights] = useState(() =>
    Object.fromEntries(types.map((t) => [t, String(s.signals.weights[t] ?? '')])),
  )
  const [halves, setHalves] = useState(() =>
    Object.fromEntries(types.map((t) => [t, String(s.signals.half_lives[t] ?? '')])),
  )
  const [invalid, setInvalid] = useState<string[]>([])

  return (
    <Form
      label="Save signal tuning"
      saving={save.isPending}
      onSave={() => {
        const bad: string[] = []
        const pick = (values: Record<string, string>) =>
          Object.fromEntries(
            types.flatMap((t) => {
              if (values[t].trim() === '') return []
              const n = parseNumber(values[t])
              if (n === null) bad.push(t)
              return n === null ? [] : [[t, n]]
            }),
          )
        const tuning = { weights: pick(weights), half_lives: pick(halves) }
        setInvalid([...new Set(bad)])
        if (bad.length === 0) save.mutate(tuning)
      }}
    >
      {types.map((t) => (
        <div key={t}>
          <NumberField
            label={`Weight for ${t} (default ${s.signal_defaults.weights[t] ?? '—'})`}
            value={weights[t]}
            onChange={(v) => setWeights({ ...weights, [t]: v })}
          />
          <NumberField
            label={`Half-life in days for ${t} (default ${s.signal_defaults.half_lives[t] ?? '—'})`}
            value={halves[t]}
            onChange={(v) => setHalves({ ...halves, [t]: v })}
          />
        </div>
      ))}
      {invalid.length > 0 && <p role="alert">Not a number: {invalid.join(', ')}.</p>}
      <Outcome write={save} />
    </Form>
  )
}

/**
 * Publish a new version of one task's prompt (ADR-140 §3).
 *
 * **Never an edit.** Every publish is a new, immutable version that becomes
 * the live one -- an audit entry naming version 3 must keep meaning the text
 * version 3 had. Going back means publishing the old text again. The button
 * names the version it will create, so nobody believes they are correcting
 * the current one in place.
 */
function PromptEditor({ task }: { task: SettingsView['ai_tasks'][number] }) {
  const publish = usePublishPrompt()
  const [body, setBody] = useState(task.prompt_body)
  const next = Math.max(0, ...task.versions.map((v) => v.version)) + 1

  return (
    <Form
      label={`Publish as version ${next}`}
      saving={publish.isPending}
      onSave={() => publish.mutate({ task: task.key, body })}
    >
      <TextField value={body} onChange={setBody}>
        <Label>Prompt for {task.label}</Label>
        <TextArea rows={10} style={{ width: '100%' }} />
      </TextField>
      {publish.isSuccess ? (
        <p role="status">
          Published as version {publish.data.version}; it is now the live prompt.
        </p>
      ) : (
        <Outcome write={publish} />
      )}
    </Form>
  )
}

function Sections({ s }: { s: SettingsView }) {
  const budget = s.ai_budget
  const signalRows = s.known_contribution_types.map((type, index) => ({
    id: index,
    type,
    weight: s.signals.weights[type],
    halfLife: s.signals.half_lives[type],
  }))

  return (
    <>
      <section aria-labelledby="sending">
        <h2 id="sending">Sending</h2>
        <SendCap s={s} />
        <dl className="facts">
          {s.channels.map((c) => (
            <div key={c.name} style={{ display: 'contents' }}>
              <dt>Channel: {c.name}</dt>
              <dd>{c.available ? 'available' : 'switched off'}</dd>
            </div>
          ))}
        </dl>
        <DataTable
          label="Delivery providers"
          columns={[
            { key: 'label', header: 'Provider', isRowHeader: true, render: (p) => p.label },
            { key: 'channels', header: 'Channels', render: (p) => p.channels.join(', ') },
            {
              key: 'credit',
              header: 'Clicks credit content',
              /**
               * ADR-182 point 4: a provider that cannot report which link was
               * clicked still sends; its clicks count for the email and teach
               * no category. Shown so nobody wonders why its sends learn less.
               */
              render: (p) => (p.click_content_attribution ? 'yes' : 'no — counted, not credited'),
            },
          ]}
          items={s.delivery_providers.map((p, index) => ({ ...p, id: index }))}
          emptyMessage="No delivery providers are registered."
        />
      </section>

      <section aria-labelledby="signals">
        <h2 id="signals">Signals</h2>
        {s.may_manage ? (
          <SignalsEditor s={s} />
        ) : (
          <DataTable
            label="Signal weights and half-lives"
            columns={[
              { key: 'type', header: 'Contribution', isRowHeader: true, render: (r) => r.type },
              { key: 'weight', header: 'Weight', render: (r) => r.weight ?? '—' },
              { key: 'half', header: 'Half-life (days)', render: (r) => r.halfLife ?? '—' },
            ]}
            items={signalRows}
            emptyMessage="No contribution types are known."
          />
        )}
      </section>

      <section aria-labelledby="ai">
        <h2 id="ai">AI</h2>
        {budget.over_warn && (
          <p role="alert">AI use has passed the warning threshold ({budget.used_pct}% of the cap).</p>
        )}
        <Provider s={s} />
        <dl className="facts">
          <dt>Default model</dt>
          <dd>
            {s.ai_model}
            {s.ai_model_from_env ? ' (set by the deployment)' : ''}
          </dd>
          {/* A yes/no only. The key itself is never sent to a browser (ADR-152). */}
          <dt>API key configured</dt>
          <dd>{s.ai_key_present ? 'yes' : 'no'}</dd>
          <dt>Tokens used</dt>
          <dd>
            {budget.tokens_used.toLocaleString()} of {budget.cap.hard_stop_tokens.toLocaleString()}{' '}
            ({budget.used_pct}%)
          </dd>
          <dt>Warning at</dt>
          <dd>{budget.cap.warn_tokens.toLocaleString()} tokens</dd>
          <dt>Spent</dt>
          <dd>
            ${budget.spend.usd.toFixed(2)} of a ${budget.cap.budget_usd.toFixed(2)} budget
            {budget.spend.unpriced_runs > 0 ? ` (${budget.spend.unpriced_runs} runs unpriced)` : ''}
          </dd>
        </dl>
        <SpendCap s={s} />

        {s.ai_tasks.map((task) => (
          <Task key={task.key} s={s} task={task} />
        ))}
      </section>
    </>
  )
}

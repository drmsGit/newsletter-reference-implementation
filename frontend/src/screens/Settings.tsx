import { useState } from 'react'
import { Input, Label, TextField } from 'react-aria-components'
import { Link } from 'react-router'

import {
  useSaveAiProvider,
  useSaveSignals,
  useSaveAiBudgetPeriod,
  useSaveSendCap,
  useSaveSessionLengths,
  useSaveSpendCap,
  useSettings,
  type SettingsView,
} from '../api/resources'
import Choice from '../components/Choice'
import DataTable from '../components/DataTable'
import DetailSection from '../components/DetailSection'
import Fact from '../components/Fact'
import { Form, Outcome } from '../components/SettingsForm'
import ScreenState from '../components/ScreenState'
import { AI_PROMPTS } from './AiPrompts'

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
    // Column 3 beside the Settings menu (task-372, render 33).
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={settings}>
          {settings.data && (
            <>
              <div className="detail-head">
                <h2>General</h2>
                <p className="muted">
                  {settings.data.may_manage
                    ? 'Changes take effect for the whole deployment, and each one is recorded in the audit log.'
                    : 'Read-only: changing settings needs permission to manage them. Every change is recorded in the audit log.'}
                </p>
              </div>
              <Sections s={settings.data} />
            </>
          )}
        </ScreenState>
      </div>
    </div>
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
      <dl className="fact-list">
        <Fact label="Most recipients one send may reach">{s.max_send_recipients}</Fact>
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

/**
 * How long a sign-in lasts (task-342; ADR-151 addendum 2026-10-11). The ranges
 * are said beside the fields; the server refuses anything outside them. A
 * shorter value signs out people past it at once; a longer lifetime reaches
 * only sign-ins after the change.
 */
function SessionLengths({ s }: { s: SettingsView }) {
  const save = useSaveSessionLengths()
  const [hours, setHours] = useState(String(s.session_absolute_hours))
  const [minutes, setMinutes] = useState(String(s.session_idle_minutes))
  const [invalid, setInvalid] = useState(false)
  if (!s.may_manage) {
    return (
      <dl className="fact-list">
        <Fact label="A sign-in lasts at most">{s.session_absolute_hours} hours</Fact>
        <Fact label="Signed out after no activity for">{s.session_idle_minutes} minutes</Fact>
      </dl>
    )
  }
  return (
    <Form
      label="Save sign-in lengths"
      saving={save.isPending}
      onSave={() => {
        const h = parseWhole(hours)
        const m = parseWhole(minutes)
        setInvalid(h === null || m === null)
        if (h !== null && m !== null) save.mutate({ absolute_hours: h, idle_minutes: m })
      }}
    >
      <NumberField label="A sign-in lasts at most (hours, 1 to 72)" value={hours} onChange={setHours} />
      <NumberField
        label="Signed out after no activity for (minutes, 5 to 480)"
        value={minutes}
        onChange={setMinutes}
      />
      <p className="muted">
        Shorter values sign out anyone past them at once. A longer lifetime applies to sign-ins after the
        change.
      </p>
      {invalid && <p role="alert">Enter whole numbers.</p>}
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
      <div className="field-pair">
        <NumberField label="Warn at (tokens)" value={warn} onChange={setWarn} />
        <NumberField label="Stop at (tokens)" value={stop} onChange={setStop} />
        <NumberField label="Budget (USD)" value={usd} onChange={setUsd} />
      </div>
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
      <dl className="fact-list">
        <Fact label="Provider">{s.ai_provider}</Fact>
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

/** How often the AI cap refills (task-345; ADR-144 addendum 2026-10-11). */
const PERIODS = [
  { id: 'month', name: 'Every month' },
  { id: 'quarter', name: 'Every quarter' },
  { id: 'year', name: 'Every year' },
  { id: 'lifetime', name: 'Never (one budget for all time)' },
]

function BudgetPeriod({ s }: { s: SettingsView }) {
  const save = useSaveAiBudgetPeriod()
  const [period, setPeriod] = useState(s.ai_budget.period ?? 'month')
  if (!s.may_manage) {
    return (
      <dl className="fact-list">
        <Fact label="The token budget refills">{PERIODS.find((p) => p.id === s.ai_budget.period)?.name ?? s.ai_budget.period}</Fact>
      </dl>
    )
  }
  return (
    <Form label="Save budget period" saving={save.isPending} onSave={() => save.mutate(period)}>
      <Choice label="The token budget refills" options={PERIODS} selected={period} onChange={setPeriod} />
      <p className="muted">Periods start at midnight UTC on the first day.</p>
      <Outcome write={save} />
    </Form>
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
        <div key={t} className="field-pair">
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
      <DetailSection id="sending" title="Sending">
        <SendCap s={s} />
        <dl className="fact-list">
          {s.channels.map((c) => (
            <Fact key={c.name} label={`Channel: ${c.name}`}>
              {c.available ? 'available' : 'switched off'}
            </Fact>
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
      </DetailSection>
      <DetailSection id="sessions" title="Sign-in sessions">
        <SessionLengths s={s} />
      </DetailSection>

      <DetailSection id="signals" title="Signals">
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
      </DetailSection>

      <DetailSection id="ai" title="AI">
        {budget.over_warn && (
          <p role="alert">AI use has passed the warning threshold ({budget.used_pct}% of the cap).</p>
        )}
        <Provider s={s} />
        <dl className="fact-list">
          <Fact label="Default model">
            {s.ai_model}
            {s.ai_model_from_env ? ' (set by the deployment)' : ''}
          </Fact>
          {/* A yes/no only. The key itself is never sent to a browser (ADR-152). */}
          <Fact label="API key configured">{s.ai_key_present ? 'yes' : 'no'}</Fact>
          <Fact label="Tokens used">
            {budget.tokens_used.toLocaleString()} of {budget.cap.hard_stop_tokens.toLocaleString()}{' '}
            ({budget.used_pct}%){' '}
            {budget.period_start
              ? `since ${new Date(budget.period_start).toLocaleDateString(undefined, { timeZone: 'UTC' })}`
              : 'in total'}
          </Fact>
          <Fact label="Warning at">{budget.cap.warn_tokens.toLocaleString()} tokens</Fact>
          <Fact label="Spent">
            ${budget.spend.usd.toFixed(2)} of a ${budget.cap.budget_usd.toFixed(2)} budget
            {budget.spend.unpriced_runs > 0 ? ` (${budget.spend.unpriced_runs} runs unpriced)` : ''}
          </Fact>
        </dl>
        <SpendCap s={s} />
        <BudgetPeriod s={s} />
      </DetailSection>
      {/* Per task, not global: its own entry (task-372, decision 23, 2026-10-17). */}
      <p className="muted quiet">
        The model, output mode and prompt of each AI task are under{' '}
        <Link to={AI_PROMPTS}>AI prompts</Link>.
      </p>
    </>
  )
}

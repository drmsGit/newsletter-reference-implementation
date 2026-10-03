import { useSettings, type SettingsView } from '../api/resources'
import DataTable from '../components/DataTable'
import ScreenState from '../components/ScreenState'
import { formatDate } from './Campaigns'

/**
 * Settings, read-only (first pass, decided 2026-10-03).
 *
 * Every value here can be changed over JSON by a person holding
 * `settings.manage` -- never by a machine, and never through an approval
 * (ADR-142's addendum) -- and every change is audited (task-245). The edit
 * controls come in a later pass; until then the screen shows what is set,
 * without a button that would suggest otherwise.
 *
 * Nothing is derived here. The budget percentage, whether the warning
 * threshold is crossed, which provider credits content -- all are the
 * server's answers.
 */
export default function Settings() {
  const settings = useSettings()

  return (
    <>
      <h1>Settings</h1>
      <p className="muted">
        Read-only for now. Changes are made by a person with permission to manage
        settings, and every change is recorded in the audit log.
      </p>
      <ScreenState query={settings}>{settings.data && <Sections s={settings.data} />}</ScreenState>
    </>
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
        <dl className="facts">
          <dt>Most recipients one send may reach</dt>
          <dd>{s.max_send_recipients}</dd>
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
        <DataTable
          label="Signal weights and half-lives"
          columns={[
            { key: 'type', header: 'Contribution', isRowHeader: true, render: (r) => r.type },
            { key: 'weight', header: 'Weight', render: (r) => r.weight ?? '—' },
            {
              key: 'half',
              header: 'Half-life (days)',
              render: (r) => r.halfLife ?? '—',
            },
          ]}
          items={signalRows}
          emptyMessage="No contribution types are known."
        />
      </section>

      <section aria-labelledby="ai">
        <h2 id="ai">AI</h2>
        {budget.over_warn && (
          <p role="alert">AI use has passed the warning threshold ({budget.used_pct}% of the cap).</p>
        )}
        <dl className="facts">
          <dt>Provider</dt>
          <dd>{s.ai_provider}</dd>
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

        {s.ai_tasks.map((task) => (
          <section key={task.key} aria-labelledby={`task-${task.key}`}>
            <h3 id={`task-${task.key}`}>{task.label}</h3>
            <p>{task.description}</p>
            <dl className="facts">
              <dt>Model</dt>
              <dd>{task.model ?? `the default (${s.ai_model})`}</dd>
              <dt>Output</dt>
              <dd>
                {/* The service's own words for the two modes (settings.service). */}
                {task.approval_mode === 'require_approval'
                  ? 'held for review'
                  : 'applied directly'}
              </dd>
              <dt>Prompt</dt>
              <dd>
                {task.prompt_version != null
                  ? `version ${task.prompt_version} of ${task.versions.length}`
                  : 'the built-in default (never published)'}
              </dd>
            </dl>
            <details>
              <summary>The live prompt</summary>
              <pre style={{ whiteSpace: 'pre-wrap' }}>{task.prompt_body}</pre>
              {task.versions.length > 0 && (
                <p className="muted">
                  Published versions:{' '}
                  {task.versions
                    .map((v) => `v${v.version} (${formatDate(v.created_at)})`)
                    .join(', ')}
                </p>
              )}
            </details>
          </section>
        ))}
      </section>
    </>
  )
}

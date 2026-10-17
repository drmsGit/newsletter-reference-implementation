import { useState } from 'react'
import { GridList, GridListItem, Label, TextArea, TextField } from 'react-aria-components'
import { useMatch, useNavigate, useParams } from 'react-router'

import {
  usePublishPrompt,
  useSetTaskApproval,
  useSetTaskModel,
  useSettings,
  type SettingsView,
} from '../api/resources'
import BackTo from '../components/BackTo'
import Choice from '../components/Choice'
import DetailOutlet from '../components/DetailOutlet'
import DetailSection from '../components/DetailSection'
import Fact from '../components/Fact'
import ScreenState from '../components/ScreenState'
import { Form, Outcome } from '../components/SettingsForm'
import { formatDate } from './Campaigns'

/**
 * The AI prompts: a part of Settings of its own (task-372, decision 23,
 * 2026-10-17; render 44). One record per AI task, the platform's own, so the
 * list has no New button and no search; each holds only that task's model,
 * output mode and prompt with its versions. The provider, the default model,
 * the key and the limits are global and stay under General.
 *
 * Who may change what is the server's answer, as on General: `may_manage`
 * for the output mode, `may_configure_ai` for the model and the prompt.
 */
export const AI_PROMPTS = '/settings/ai-prompts'

type Task = SettingsView['ai_tasks'][number]

const DEFAULT_MODEL = '__default__'

function outputLine(task: Task): string {
  if (!task.held_form) return 'no approval step'
  return task.approval_mode === 'require_approval' ? 'held for review' : 'applied directly'
}

function promptLine(task: Task): string {
  return task.prompt_version != null
    ? `version ${task.prompt_version} of ${task.versions.length}`
    : 'the built-in default (never published)'
}

/** Column 2: the four tasks, each with its model, output and prompt in a line. */
export default function AiPrompts() {
  const settings = useSettings()
  const navigate = useNavigate()
  const open = useMatch(`${AI_PROMPTS}/:key`)?.params.key
  return (
    <>
      <div className="list-head">
        <BackTo to="/settings" label="Settings" />
        <h1>AI prompts</h1>
        <p className="muted list-note">
          One per AI task: its model, its output mode and its prompt. The provider, the limits and the budget are
          under General.
        </p>
      </div>
      <ScreenState query={settings}>
        <GridList
          aria-label="AI tasks"
          className="react-aria-GridList item-list"
          items={(settings.data?.ai_tasks ?? []).map((t) => ({ ...t, id: t.key }))}
          selectionMode="single"
          selectionBehavior="replace"
          selectedKeys={open !== undefined ? [open] : []}
          onSelectionChange={(keys) => {
            const [key] = keys === 'all' ? [] : [...keys]
            if (key !== undefined && String(key) !== open) navigate(`${AI_PROMPTS}/${key}`)
          }}
          renderEmptyState={() => <p className="list-empty muted">No AI tasks are registered.</p>}
        >
          {(t) => (
            <GridListItem id={t.key} textValue={t.label} className="react-aria-GridListItem item">
              <span className="item-title">{t.label}</span>
              <span className="item-summary muted">
                Model: {t.model ?? 'the default'} · Output: {outputLine(t)}
              </span>
              <span className="item-summary muted">Prompt: {promptLine(t)}</span>
            </GridListItem>
          )}
        </GridList>
      </ScreenState>
    </>
  )
}

/** Column 3: one task (render 44). */
export function AiPromptDetail() {
  const { key } = useParams()
  const settings = useSettings()
  const task = settings.data?.ai_tasks.find((t) => t.key === key)
  return (
    <div className="detail">
      <div className="detail-scroll">
        <ScreenState query={settings}>
          {settings.data &&
            (task ? (
              <>
                <div className="detail-head">
                  <h2>{task.label}</h2>
                  <p className="muted">{task.description}</p>
                </div>
                {/* Keyed by the task: a choice made on one is not carried to the next (doc-33). */}
                <TaskSettings key={task.key} s={settings.data} task={task} />
              </>
            ) : (
              <p role="alert" className="quiet">There is no AI task called {key}.</p>
            ))}
        </ScreenState>
      </div>
    </div>
  )
}

/** The tasks as a split: the list in column 2, the open task in column 3. */
export function AiPromptsSplit() {
  return (
    <div className="split">
      <section className="col-list" aria-label="AI prompt list">
        <AiPrompts />
      </section>
      <section className="col-detail">
        <DetailOutlet />
      </section>
    </div>
  )
}

export function NoTaskOpen() {
  return <p className="detail-placeholder muted">Select an AI task to see its model, output and prompt.</p>
}

function TaskSettings({ s, task }: { s: SettingsView; task: Task }) {
  const approval = useSetTaskApproval()
  const model = useSetTaskModel()
  const [mode, setMode] = useState(task.approval_mode)
  const [chosen, setChosen] = useState(task.model ?? DEFAULT_MODEL)

  return (
    <>
      <DetailSection id="task-model" title="Model">
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
        <dl className="fact-list">
          <Fact label="Model">{task.model ?? `the default (${s.ai_model})`}</Fact>
        </dl>
      )}
      </DetailSection>

      <DetailSection id="task-output" title="Output">
      {!task.held_form ? (
        // Nothing to hold: the output only appears where a person takes it
        // themselves (ADR-140 addendum 2026-10-16), so no switch is offered.
        <dl className="fact-list">
          <Fact label="Output">no approval step — it only appears where a person takes it themselves</Fact>
        </dl>
      ) : s.may_manage ? (
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
        <dl className="fact-list">
          <Fact label="Output">{task.approval_mode === 'require_approval' ? 'held for review' : 'applied directly'}</Fact>
        </dl>
      )}
      </DetailSection>

      <DetailSection id="task-prompt" title="Prompt">
      <dl className="fact-list">
        <Fact label="Prompt">{promptLine(task)}</Fact>
      </dl>
      {s.may_configure_ai && <PromptEditor task={task} />}
      <details className="live-prompt">
        <summary>The live prompt</summary>
        <pre style={{ whiteSpace: 'pre-wrap' }}>{task.prompt_body}</pre>
        {task.versions.length > 0 && (
          <p className="muted">
            Published versions:{' '}
            {task.versions.map((v) => `v${v.version} (${formatDate(v.created_at)})`).join(', ')}
          </p>
        )}
      </details>
      </DetailSection>
    </>
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
function PromptEditor({ task }: { task: Task }) {
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
        <TextArea rows={10} />
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


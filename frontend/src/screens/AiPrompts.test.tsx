import { fireEvent, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { Route, Routes } from 'react-router'

import { AI_PROMPTS, AiPromptDetail, AiPromptsSplit, NoTaskOpen } from './AiPrompts'
import { jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

function task(key: string, label: string, extra: object = {}) {
  return {
    key, label, description: `${label} does its job.`, prompt_body: 'Write well.', prompt_version: null,
    versions: [], model: null, approval_mode: 'require_approval', held_form: true, ...extra,
  }
}

const SETTINGS = {
  ai_model: 'model-1',
  governed_models: ['model-1', 'model-2'],
  ai_tasks: [
    task('content_draft', 'Content draft', { held_form: false, approval_mode: 'auto_apply' }),
    task('subject_preheader', 'Subject & preheader', { model: 'model-2', prompt_version: 2,
      versions: [{ version: 1 }, { version: 2 }] }),
  ],
  may_manage: true,
  may_configure_ai: false,
}

function open(route: string) {
  stubFetch({ 'GET /settings': () => jsonResponse(SETTINGS) })
  renderWithProviders(
    <Routes>
      <Route element={<AiPromptsSplit />}>
        <Route path={AI_PROMPTS} element={<NoTaskOpen />} />
        <Route path={`${AI_PROMPTS}/:key`} element={<AiPromptDetail />} />
      </Route>
    </Routes>,
    { route },
  )
}

describe('the AI prompts (task-372, decision 23)', () => {
  it('lists each task with its model, output and prompt, and opens one beside the list', async () => {
    open(AI_PROMPTS)
    const list = await screen.findByRole('grid', { name: 'AI tasks' })
    const subject = within(list).getByRole('row', { name: /Subject & preheader/ })
    expect(subject).toHaveTextContent('Model: model-2 · Output: held for review')
    expect(subject).toHaveTextContent('Prompt: version 2 of 2')
    expect(within(list).getByRole('row', { name: /Content draft/ })).toHaveTextContent(
      'Model: the default · Output: no approval step',
    )
    // The platform's own tasks: nothing to create.
    expect(screen.queryByRole('button', { name: /New/ })).not.toBeInTheDocument()
    fireEvent.click(within(list).getByText('Subject & preheader'))
    expect(await screen.findByRole('heading', { name: 'Subject & preheader', level: 2 })).toBeInTheDocument()
    expect(subject).toHaveAttribute('aria-selected', 'true')
  })

  it('does not carry an output mode chosen on one task to the next', async () => {
    const two = { ...SETTINGS, ai_tasks: [SETTINGS.ai_tasks[1], task('content_translate', 'Content translation',
      { approval_mode: 'auto_apply' })] }
    stubFetch({ 'GET /settings': () => jsonResponse(two) })
    renderWithProviders(
      <Routes>
        <Route element={<AiPromptsSplit />}>
          <Route path={`${AI_PROMPTS}/:key`} element={<AiPromptDetail />} />
        </Route>
      </Routes>,
      { route: `${AI_PROMPTS}/subject_preheader` },
    )
    fireEvent.click(await screen.findByRole('button', { name: /Output of Subject & preheader/ }))
    fireEvent.click(await screen.findByRole('option', { name: 'applied directly' }))
    fireEvent.click(within(screen.getByRole('grid', { name: 'AI tasks' })).getByText('Content translation'))
    // Its own stored mode, not the one just chosen on the other task.
    expect(await screen.findByRole('button', { name: /Output of Content translation/ })).toHaveTextContent(
      'applied directly',
    )
    fireEvent.click(within(screen.getByRole('grid', { name: 'AI tasks' })).getByText('Subject & preheader'))
    expect(await screen.findByRole('button', { name: /Output of Subject & preheader/ })).toHaveTextContent(
      'held for review',
    )
  })
})

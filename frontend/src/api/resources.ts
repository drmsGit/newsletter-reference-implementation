import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { PAGE_SIZE } from '../components/Pager'
import { api } from './client'
import { HttpError } from './session'
import type { components } from './schema'

export type Campaign = components['schemas']['Campaign']
export type ContentRecord = components['schemas']['ContentRecord']
export type AudienceGroup = components['schemas']['AudienceGroup']
export type PendingActionRow = components['schemas']['PendingActionRow']
export type PendingActionDetail = components['schemas']['PendingActionDetail']
export type SendInstanceListed = components['schemas']['SendInstanceListed']
export type DeliveryExecution = components['schemas']['DeliveryExecution']
export type DeliveryAsSent = components['schemas']['DeliveryAsSent']
export type CampaignComposition = components['schemas']['CampaignComposition']
export type MonitoredCampaign = components['schemas']['MonitoredCampaign']
export type SettingsView = components['schemas']['Settings']
export type ComposedVariant = components['schemas']['ComposedVariant']
export type ComposedModule = components['schemas']['ComposedModule']
export type VariantDuplicated = components['schemas']['VariantDuplicated']

/**
 * **Every key here names its resource, and none mentions the brand.**
 *
 * TanStack Query stores each answer under a key. Switching brand calls
 * `invalidateQueries()` with no filter, which marks every key stale at once --
 * so these do not need the brand, and deliberately omit it.
 *
 * Including it would be worse rather than more precise. The working brand lives
 * in the session on the server (ADR-172), so a key built from a client-side
 * copy would be a second answer to "which brand is this?", free to disagree
 * with the first.
 */
export const keys = {
  campaigns: ['campaigns'] as const,
  composition: (id: number) => ['campaigns', id, 'composition'] as const,
  monitoring: ['campaigns', 'monitoring'] as const,
  settings: ['settings'] as const,
  content: ['content'] as const,
  contentRecord: (id: number) => ['content', id] as const,
  audienceGroups: ['audience-groups'] as const,
  audienceGroup: (id: number) => ['audience-groups', id] as const,
  approvals: ['approvals'] as const,
  approval: (id: number) => ['approvals', id] as const,
  deliveries: ['deliveries'] as const,
  delivery: (id: number) => ['deliveries', id] as const,
  deliveryExecutions: (id: number) => ['deliveries', id, 'executions'] as const,
  asSent: (executionId: number) => ['executions', executionId, 'as-sent'] as const,
}

/**
 * Await a request and hand back its body, or throw.
 *
 * `fetch` does not throw on a 404 or a 500 -- it resolves with a response that
 * says so -- while TanStack Query decides success or failure by whether the
 * function throws. This is the one place that translates between the two, so
 * no screen has to remember to check.
 */
async function read<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const result = await call
  if (!result.response.ok) {
    const detail = (result.error as { detail?: unknown } | undefined)?.detail
    throw new HttpError(result.response.status, typeof detail === 'string' ? detail : undefined)
  }
  return result.data as T
}

export function useCampaigns(offset = 0) {
  return useQuery({
    queryKey: [...keys.campaigns, 'page', offset],
    queryFn: () =>
      read(api.GET('/campaigns/', { params: { query: { limit: PAGE_SIZE, offset } } })),
  })
}

export function useContentList(offset = 0) {
  return useQuery({
    queryKey: [...keys.content, 'page', offset],
    queryFn: () =>
      read(api.GET('/content/', { params: { query: { limit: PAGE_SIZE, offset } } })),
  })
}

export function useContentRecord(id: number) {
  return useQuery({
    queryKey: keys.contentRecord(id),
    queryFn: () =>
      read(api.GET('/content/{content_id}', { params: { path: { content_id: id } } })),
  })
}

export function useAudienceGroups(offset = 0) {
  return useQuery({
    queryKey: [...keys.audienceGroups, 'page', offset],
    queryFn: () =>
      read(api.GET('/api/audience-groups/', { params: { query: { limit: PAGE_SIZE, offset } } })),
  })
}

export function useAudienceGroup(id: number) {
  return useQuery({
    queryKey: keys.audienceGroup(id),
    queryFn: () =>
      read(api.GET('/api/audience-groups/{group_id}', { params: { path: { group_id: id } } })),
  })
}

/** The inbox's narrowing and paging (task-209): every field optional. */
export type ApprovalQuery = {
  status?: 'pending' | 'decided' | 'all'
  action_key?: string
  requested_by_type?: string
  requested_by_id?: number
  limit?: number
  offset?: number
}

/**
 * The inbox, narrowed. The query is part of the key, so each filter combination
 * is cached on its own -- and still under `keys.approvals`, so anything that
 * invalidates the inbox (a decision) invalidates every filtered view of it.
 */
export function useApprovals(query: ApprovalQuery = {}) {
  return useQuery({
    queryKey: [...keys.approvals, 'list', query],
    queryFn: () => read(api.GET('/approvals/', { params: { query } })),
  })
}

/** What this brand's inbox can be narrowed by: only values its requests carry. */
export function useApprovalFilterOptions() {
  return useQuery({
    queryKey: [...keys.approvals, 'filter-options'],
    queryFn: () => read(api.GET('/approvals/filter-options')),
  })
}

export function useApproval(id: number) {
  return useQuery({
    queryKey: keys.approval(id),
    queryFn: () =>
      read(api.GET('/approvals/{pending_id}', { params: { path: { pending_id: id } } })),
  })
}

/** One ADR-185 page of sends, newest first. */
export function useDeliveries(offset = 0) {
  return useQuery({
    queryKey: [...keys.deliveries, 'page', offset],
    queryFn: () =>
      read(api.GET('/delivery/send-instances', { params: { query: { limit: PAGE_SIZE, offset } } })),
  })
}

export function useDelivery(id: number) {
  return useQuery({
    queryKey: keys.delivery(id),
    queryFn: () =>
      read(
        api.GET('/delivery/send-instances/{send_instance_id}', {
          params: { path: { send_instance_id: id } },
        }),
      ),
  })
}

/** One ADR-185 page of a send's recipients, newest first. */
export function useDeliveryExecutions(id: number, offset = 0) {
  return useQuery({
    queryKey: [...keys.deliveryExecutions(id), 'page', offset],
    queryFn: () =>
      read(
        api.GET('/delivery/send-instances/{send_instance_id}/executions', {
          params: { path: { send_instance_id: id }, query: { limit: PAGE_SIZE, offset } },
        }),
      ),
  })
}

/**
 * What one recipient got (ADR-183). Answers 409 for an execution that was not
 * sent, or was sent before delivery records existed -- the screen tells that
 * apart from a failure, since it is an answer and not an error.
 */
export function useAsSent(executionId: number) {
  return useQuery({
    queryKey: keys.asSent(executionId),
    queryFn: () =>
      read(
        api.GET('/delivery/executions/{execution_id}/as-sent', {
          params: { path: { execution_id: executionId } },
        }),
      ),
  })
}

/** A campaign as the variant editor shows it (B11): one read for the screen. */
export function useComposition(campaignId: number) {
  return useQuery({
    queryKey: keys.composition(campaignId),
    queryFn: () =>
      read(
        api.GET('/campaigns/{campaign_id}/composition', {
          params: { path: { campaign_id: campaignId } },
        }),
      ),
  })
}

/**
 * Duplicate a variant beside its original (task-229).
 *
 * **The body is empty on purpose.** Which content mode a copy takes is the
 * server's rule -- `keep` inside the variant's own campaign, `layout` into
 * another -- and sending one from here would be a second copy of it, free to
 * disagree. The response says which mode was used.
 *
 * Not idempotent: each call makes another copy. The screen disables the button
 * while a call is in flight, which is the whole of the double-click defence.
 */
export function useDuplicateVariant(campaignId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (variantId: number) =>
      read(
        api.POST('/campaigns/variants/{variant_id}/duplicate', {
          params: { path: { variant_id: variantId } },
          body: {},
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.composition(campaignId) }),
  })
}

/**
 * Where every campaign is (task-216): in flight, in preparation, or sent.
 * Derived by the server from snapshots and sends -- this client never works a
 * state out for itself, so the definition of "in flight" lives in one place.
 */
export function useMonitoring(offset = 0) {
  return useQuery({
    queryKey: [...keys.monitoring, 'page', offset],
    queryFn: () =>
      read(api.GET('/campaigns/monitoring', { params: { query: { limit: PAGE_SIZE, offset } } })),
  })
}

/** Everything the settings screen shows. Readable with `view`. */
export function useSettings() {
  return useQuery({
    queryKey: keys.settings,
    queryFn: () => read(api.GET('/settings')),
  })
}

/**
 * The settings writes (2026-10-03). Each one re-reads the whole settings view
 * on success, because the server normalises what it stores -- a spend cap's
 * warning is clamped to its hard stop, an unknown approval mode clears to the
 * default -- and the screen should show what was kept, not what was typed.
 * Every one of these is audited server-side (task-245).
 */
function useSettingsWrite<V, R>(write: (value: V) => Promise<R>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: write,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.settings }),
  })
}

export function useSaveSendCap() {
  return useSettingsWrite((cap: number) =>
    read(api.PUT('/settings/send-cap', { body: { max_send_recipients: cap } })),
  )
}

export function useSaveSpendCap() {
  return useSettingsWrite(
    (cap: { warn_tokens: number; hard_stop_tokens: number; budget_usd: number }) =>
      read(api.PUT('/settings/ai/spend-cap', { body: cap })),
  )
}

export function useSaveAiProvider() {
  return useSettingsWrite((provider: string) =>
    read(api.PUT('/settings/ai/provider', { body: { provider } })),
  )
}

export function useSetTaskApproval() {
  return useSettingsWrite(
    ({ task, mode }: { task: string; mode: 'auto_apply' | 'require_approval' }) =>
      read(
        api.PUT('/settings/ai/tasks/{task_key}/approval', {
          params: { path: { task_key: task } },
          body: { mode },
        }),
      ),
  )
}

export function useSetTaskModel() {
  return useSettingsWrite(({ task, model }: { task: string; model: string | null }) =>
    read(
      api.PUT('/settings/ai/tasks/{task_key}/model', {
        params: { path: { task_key: task } },
        body: { model },
      }),
    ),
  )
}

/** Replace the signal tuning. A type left out goes back to its code default. */
export function useSaveSignals() {
  return useSettingsWrite(
    (tuning: { weights: Record<string, number>; half_lives: Record<string, number> }) =>
      read(api.PUT('/settings/signals', { body: tuning })),
  )
}

/**
 * Publish a new prompt version (ADR-140 §3): never an edit, always a new
 * immutable version that becomes the live one. Needs `ai.run` as well.
 */
export function usePublishPrompt() {
  return useSettingsWrite(({ task, body }: { task: string; body: string }) =>
    read(
      api.POST('/settings/ai/tasks/{task_key}/prompt', {
        params: { path: { task_key: task } },
        body: { body },
      }),
    ),
  )
}

/**
 * Decide a held action. Approving RUNS it (ADR-142 §4) -- for a held send,
 * that fires the send -- which the screen says on the button.
 *
 * A reason is optional on both, never required (Manager Workflow Q1.5: a
 * required field produces `---`, not reasons). A pick-one passes the index of
 * the chosen option; the action refuses without one rather than defaulting.
 *
 * Re-reads everything under `keys.approvals`: the detail (its status changed),
 * every filtered inbox view (the request left "waiting") and the filter
 * options.
 */
export function useDecide(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      verdict,
      reason,
      choice,
    }: {
      verdict: 'approve' | 'reject'
      reason?: string
      choice?: number
    }) => {
      const body = { reason: reason?.trim() || null, choice_index: choice ?? null }
      const path = { params: { path: { pending_id: id } }, body }
      return read(
        verdict === 'approve'
          ? api.POST('/approvals/{pending_id}/approve', path)
          : api.POST('/approvals/{pending_id}/reject', path),
      )
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.approvals }),
  })
}

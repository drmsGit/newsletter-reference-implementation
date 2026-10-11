import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { PAGE_SIZE } from '../components/Pager'
import { api } from './client'
import { HttpError } from './session'
import type { components } from './schema'

export type Campaign = components['schemas']['Campaign']
export type ContentRecord = components['schemas']['ContentRecord']
export type ContentListItem = components['schemas']['ContentListItem']
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
export type DecisionSlotListed = components['schemas']['DecisionSlotListed']
export type SlotTopContent = components['schemas']['SlotTopContent']
export type SlotResolution = components['schemas']['SlotResolution']

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
  decisionSlots: ['decision-slots'] as const,
  decisionSlot: (id: number) => ['decision-slots', id] as const,
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
  brandProfiles: ['brand-profiles'] as const,
  brandProfile: (id: number) => ['brand-profiles', id] as const,
  brandProfileStructure: ['brand-profile-structure'] as const,
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
    throw HttpError.from(result.response.status, detail)
  }
  return result.data as T
}

export function useCampaigns(offset = 0, q = '') {
  return useQuery({
    queryKey: [...keys.campaigns, 'page', offset, q],
    queryFn: () =>
      read(api.GET('/campaigns/', { params: { query: { limit: PAGE_SIZE, offset, q: q || undefined } } })),
  })
}

export function useContentList(
  offset = 0,
  q = '',
  status?: 'active' | 'inactive',
  categoryId: number | null = null,
  readyFor: string | null = null,
) {
  return useQuery({
    queryKey: [...keys.content, 'page', offset, q, status, categoryId, readyFor],
    queryFn: () =>
      read(
        api.GET('/content/', {
          params: {
            query: {
              limit: PAGE_SIZE, offset, q: q || undefined, status, category_id: categoryId ?? undefined,
              ready_for: readyFor ?? undefined,
            },
          },
        }),
      ),
  })
}

export function useContentRecord(id: number) {
  return useQuery({
    queryKey: keys.contentRecord(id),
    queryFn: () =>
      read(api.GET('/content/{content_id}', { params: { path: { content_id: id } } })),
  })
}

export function useAudienceGroups(offset = 0, q = '') {
  return useQuery({
    queryKey: [...keys.audienceGroups, 'page', offset, q],
    queryFn: () =>
      read(
        api.GET('/api/audience-groups/', {
          params: { query: { limit: PAGE_SIZE, offset, q: q || undefined } },
        }),
      ),
  })
}

/** The recipient list, found by identifier or address on the server (task-292). */
export function useRecipients(offset = 0, q = '') {
  return useQuery({
    queryKey: ['recipients', 'page', offset, q],
    queryFn: () => read(api.GET('/recipients/', { params: { query: { limit: PAGE_SIZE, offset, q: q || undefined } } })),
  })
}

/** One person as the recipient page shows them, from the working brand (task-50). */
export function useRecipientActivity(id: number) {
  return useQuery({
    queryKey: ['recipients', id, 'activity'],
    queryFn: () => read(api.GET('/recipients/{recipient_id}/activity', { params: { path: { recipient_id: id } } })),
  })
}

/** Which groups the person is in on `channel`, and why, as of now (task-214). */
export function useRecipientGroups(id: number, channel: string, offset = 0) {
  return useQuery({
    queryKey: ['recipients', id, 'audience-groups', channel, offset],
    queryFn: () =>
      read(api.GET('/recipients/{recipient_id}/audience-groups', {
        params: { path: { recipient_id: id }, query: { channel, limit: PAGE_SIZE, offset } },
      })),
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

/**
 * The brand's sent sends, newest first, for an audience rule to name one
 * (task-298). One page: the route has no search, so an older send is reached
 * through its campaign instead.
 */
export function useSentSends() {
  return useQuery({
    queryKey: [...keys.deliveries, 'sent'],
    queryFn: () =>
      read(api.GET('/delivery/send-instances', { params: { query: { status: 'sent', limit: PAGE_SIZE, offset: 0 } } })),
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

/**
 * Release a send stranded in 'sending' (ADR-192): it becomes 'failed', so a
 * retry may run. People only; refused unless the send is stranded right now.
 */
export function useReleaseDelivery(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      read(
        api.POST('/delivery/send-instances/{send_instance_id}/release', {
          params: { path: { send_instance_id: id } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['deliveries'] }),
  })
}

/** How many recipients a screen shows before the person searches. */
export const SAMPLE_SIZE = 20

/**
 * A send's first twenty recipients, newest first, or the ones matching `q`
 * (identifier or address), with how many match in all. A sample and a search,
 * not a paged list -- decided with the user 2026-10-03.
 */
export function useDeliveryExecutions(id: number, q = '') {
  return useQuery({
    queryKey: [...keys.deliveryExecutions(id), 'search', q],
    queryFn: () =>
      read(
        api.GET('/delivery/send-instances/{send_instance_id}/executions', {
          params: {
            path: { send_instance_id: id },
            query: { limit: SAMPLE_SIZE, offset: 0, q: q || undefined },
          },
        }),
      ),
  })
}

/**
 * What a send to this group on `channel` would reach: each rule block's count,
 * resolved vs reachable and why the rest drop (task-50, B27), plus the first
 * twenty reachable recipients -- or those matching `q` -- and how many match.
 */
export function useAudiencePreview(id: number, channel: string, q = '') {
  return useQuery({
    queryKey: [...keys.audienceGroup(id), 'preview', channel, q],
    queryFn: () =>
      read(
        api.GET('/api/audience-groups/{group_id}/preview', {
          params: { path: { group_id: id }, query: { channel, q: q || undefined } },
        }),
      ),
  })
}

// --- the audience editor (task-297) ------------------------------------------

export type AudienceRuleBlock = components['schemas']['AudienceRuleBlock']
export type AudienceGroupMember = components['schemas']['AudienceGroupMember']
export type PastePreview = components['schemas']['PastePreview']

/** A group's rules, in order. Under the group's key, so any write re-reads them. */
export function useAudienceBlocks(id: number) {
  return useQuery({
    queryKey: [...keys.audienceGroup(id), 'blocks'],
    queryFn: () => read(api.GET('/api/audience-groups/{group_id}/blocks', { params: { path: { group_id: id } } })),
  })
}

/**
 * The people added by hand, each named, with whom an exclusion leaves out on
 * `channel` (ADR-176 point 1: an exclusion beats a hand-add).
 */
export function useAudienceMembers(id: number, channel: string, offset = 0) {
  return useQuery({
    queryKey: [...keys.audienceGroup(id), 'members', channel, offset],
    queryFn: () =>
      read(api.GET('/api/audience-groups/{group_id}/members', {
        params: { path: { group_id: id }, query: { channel, limit: PAGE_SIZE, offset } },
      })),
  })
}

/** The languages and statuses the brand's recipients hold, for a rule to choose from. */
export function useCriteriaValues() {
  return useQuery({
    queryKey: [...keys.audienceGroups, 'criteria-values'],
    queryFn: () => read(api.GET('/api/audience-groups/criteria-values')),
  })
}

export function useCreateAudience() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ name, description }: { name: string; description: string }) =>
      read(api.POST('/api/audience-groups/', { body: { name, description: description || null } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...keys.audienceGroups, 'page'] }),
  })
}

/** A new group with one suggested rule per top category of a campaign's content (4.1). */
export function useSuggestAudience() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (campaignId: number) =>
      read(api.POST('/api/audience-groups/suggested', { body: { campaign_id: campaignId } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...keys.audienceGroups, 'page'] }),
  })
}

/**
 * One write to a group, stating its version (design pass decision 10).
 *
 * **The group has one version for everything** — a rename, a rule, a hand-add
 * all move its `updated_at` — so every write reads it from the cache when it
 * is sent, and all of them run one after another in one queue, as the
 * composer's do (task-110). A write's success waits for the group to be read
 * again, so the next one states the version this one produced; the rules,
 * people and arithmetic are re-read alongside without holding the queue.
 */
function useAudienceWrite<TArgs, TResult>(
  id: number,
  send: (args: TArgs, version: string | undefined) => Promise<TResult>,
) {
  const queryClient = useQueryClient()
  const key = keys.audienceGroup(id)
  return useMutation({
    scope: { id: `audience-${id}` },
    mutationFn: (args: TArgs) => send(args, queryClient.getQueryData<AudienceGroup>(key)?.updated_at),
    onSuccess: async () => {
      void queryClient.invalidateQueries({ queryKey: key, predicate: (q) => q.queryKey.length > key.length })
      void queryClient.invalidateQueries({ queryKey: [...keys.audienceGroups, 'page'] })
      await queryClient.invalidateQueries({ queryKey: key, exact: true })
    },
  })
}

const groupPath = (id: number, version: string | undefined) => ({
  path: { group_id: id },
  header: { 'If-Match': version },
})

/** Rename or re-describe: only what is sent changes. */
export function useSaveAudience(id: number) {
  return useAudienceWrite(id, (changes: { name?: string; description?: string | null }, version) =>
    read(api.PATCH('/api/audience-groups/{group_id}', { params: groupPath(id, version), body: changes })))
}

export type RuleChanges = { kind?: string; criteria?: Record<string, unknown>; label?: string | null }

export function useAddRule(id: number) {
  return useAudienceWrite(id, (rule: RuleChanges & { kind: string }, version) =>
    read(api.POST('/api/audience-groups/{group_id}/blocks', { params: groupPath(id, version), body: rule })))
}

export function useSaveRule(id: number) {
  return useAudienceWrite(id, ({ blockId, ...changes }: RuleChanges & { blockId: number }, version) =>
    read(api.PATCH('/api/audience-groups/{group_id}/blocks/{block_id}', {
      params: { ...groupPath(id, version), path: { group_id: id, block_id: blockId } },
      body: changes,
    })))
}

export function useRemoveRule(id: number) {
  return useAudienceWrite(id, (blockId: number, version) =>
    read(api.DELETE('/api/audience-groups/{group_id}/blocks/{block_id}', {
      params: { ...groupPath(id, version), path: { group_id: id, block_id: blockId } },
    })))
}

/** Add one person by hand with an optional reason; who and when the server records. */
export function useAddPerson(id: number) {
  return useAudienceWrite(id, ({ recipientId, reason }: { recipientId: number; reason: string }, version) =>
    read(api.POST('/api/audience-groups/{group_id}/members/{recipient_id}', {
      params: { ...groupPath(id, version), path: { group_id: id, recipient_id: recipientId } },
      body: { reason: reason || null },
    })))
}

export function useRemovePerson(id: number) {
  return useAudienceWrite(id, (recipientId: number, version) =>
    read(api.DELETE('/api/audience-groups/{group_id}/members/{recipient_id}', {
      params: { ...groupPath(id, version), path: { group_id: id, recipient_id: recipientId } },
    })))
}

/** What a paste would do, before anything is added (decision 6). Writes nothing. */
export function usePastePreview(id: number) {
  return useMutation({
    mutationFn: ({ text, channel }: { text: string; channel: string }) =>
      read(api.POST('/api/audience-groups/{group_id}/members/paste-preview', {
        params: { path: { group_id: id } }, body: { text, channel },
      })),
  })
}

export function usePastePeople(id: number) {
  return useAudienceWrite(id, ({ text, reason }: { text: string; reason: string }, version) =>
    read(api.POST('/api/audience-groups/{group_id}/members/paste', {
      params: groupPath(id, version), body: { text, reason: reason || null },
    })))
}

/** Re-derive the suggested rules from the source campaign; the manager's own stay (4.7). */
export function useRecalculate(id: number) {
  return useAudienceWrite(id, () =>
    read(api.POST('/api/audience-groups/{group_id}/recalculate', { params: { path: { group_id: id } } })))
}

/**
 * Delete a group no send uses. Not through the queue's re-read: a deleted
 * group answers 404, so its cache is dropped instead of refreshed.
 */
export function useDeleteAudience(id: number) {
  const queryClient = useQueryClient()
  const key = keys.audienceGroup(id)
  return useMutation({
    scope: { id: `audience-${id}` },
    mutationFn: () =>
      read(api.DELETE('/api/audience-groups/{group_id}', {
        params: groupPath(id, queryClient.getQueryData<AudienceGroup>(key)?.updated_at),
      })),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: key })
      return queryClient.invalidateQueries({ queryKey: [...keys.audienceGroups, 'page'] })
    },
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

/** Every decision slot in the brand, with what it has picked (inventory B21). */
export function useDecisionSlots(offset = 0) {
  return useQuery({
    queryKey: [...keys.decisionSlots, 'page', offset],
    queryFn: () =>
      read(api.GET('/campaigns/decision-slots', { params: { query: { limit: PAGE_SIZE, offset } } })),
  })
}

/**
 * One slot and what it has picked: summary, top content with its share, the
 * latest picks and the reasons given (inventory B22, task-211).
 */
export function useDecisionSlotStats(id: number) {
  return useQuery({
    queryKey: [...keys.decisionSlot(id), 'stats'],
    queryFn: () =>
      read(api.GET('/campaigns/decision-slots/{slot_id}/stats', { params: { path: { slot_id: id } } })),
  })
}

/**
 * How many content records the slot would choose between (task-205). A GET
 * that resolves nothing -- unlike execute, which writes a pick -- so opening
 * the screen never changes what the slot has done.
 */
export function useSlotCandidates(id: number) {
  return useQuery({
    queryKey: [...keys.decisionSlot(id), 'candidates'],
    queryFn: () =>
      read(
        api.GET('/campaigns/decision-slots/{slot_id}/candidates', { params: { path: { slot_id: id } } }),
      ),
  })
}

// --- the variant editor's writes (task-255) ----------------------------------

export type ModuleManifest = components['schemas']['ModuleManifestOut']
export type ModuleVariable = components['schemas']['ModuleVariableOut']

/** The modules a channel offers, with each field as an authoring form needs it. */
export function useModuleManifests(channel: string | undefined) {
  return useQuery({
    queryKey: ['modules', channel],
    queryFn: () => read(api.GET('/modules', { params: { query: { channel: channel! } } })),
    enabled: !!channel,
    // Manifests are files the backend reads at startup. Cached until a page
    // reload or a brand switch (which invalidates everything, session.ts) —
    // not across a backend deploy, so an open tab keeps the old field list
    // until it reloads (interview review 2026-10-09, Client Q2; task-55).
    staleTime: Infinity,
  })
}


type Variant = CampaignComposition['variants'][number]['variant']

/**
 * The entity a save is about, as the cache holds it **when the save is sent**,
 * not when the field was edited.
 *
 * Two fields of one module blurred in quick succession make two saves. The
 * second must carry the version the first one produced (task-110), or it is
 * refused as stale against the person's own edit — and it must merge into the
 * data the first one wrote, or it writes the first field's old value back.
 * So saves run one after another (`scope`); each one's success waits for the
 * composition to be read again before the next starts, and each reads the
 * entity from that fresh read at its own start. A save states only what
 * changed (`changes`), never a copy of the whole entity taken at edit time.
 */
function cachedOf(composition: CampaignComposition | undefined, kind: 'variant', id: number): Variant | undefined
function cachedOf(composition: CampaignComposition | undefined, kind: 'module', id: number): ComposedModule | undefined
function cachedOf(composition: CampaignComposition | undefined, kind: 'variant' | 'module', id: number) {
  for (const composed of composition?.variants ?? []) {
    if (kind === 'variant' && composed.variant.id === id) return composed.variant
    if (kind === 'module') {
      const found = composed.modules.find((m) => m.id === id)
      if (found) return found
    }
  }
  return undefined
}

function useComposerWrite<TArgs extends { id: number }, TEntity, TResult>(
  campaignId: number,
  kind: 'variant' | 'module',
  current: (composition: CampaignComposition | undefined, id: number) => TEntity | undefined,
  send: (args: TArgs, entity: TEntity | undefined) => Promise<TResult>,
) {
  const queryClient = useQueryClient()
  const key = keys.composition(campaignId)
  return useMutation({
    // One queue per kind of entity: every module write on the screen waits for
    // the one before it, and so does every variant write. A scope is fixed per
    // hook rather than per call, so this is coarser than one queue per module;
    // the cost is a little latency between saves, never a refused one.
    scope: { id: `composer-${kind}` },
    mutationFn: (args: TArgs) =>
      send(args, current(queryClient.getQueryData<CampaignComposition>(key), args.id)),
    // Returned, so the mutation — and the next one queued behind it — waits
    // for the re-read that carries the new version.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  })
}

/**
 * Change some of a variant's name, subject and preheader. The PUT replaces all
 * three, so the ones not changed are sent as the cache holds them now.
 */
export function useSaveVariant(campaignId: number) {
  return useComposerWrite(
    campaignId,
    'variant',
    (composition, id) => cachedOf(composition, 'variant', id),
    (
      // `envelope` replaces the stored one when sent and is left alone when
      // not (task-48), so a rename cannot clear the subject.
      {
        id,
        changes,
      }: {
        id: number
        changes: { name?: string; envelope?: Record<string, string | null>; brand_profile_id?: number }
      },
      variant,
    ) =>
      read(
        api.PUT('/campaigns/variants/{variant_id}', {
          params: { path: { variant_id: id }, header: { 'If-Match': variant?.updated_at } },
          body: { name: variant?.name ?? '', ...changes },
        }),
      ),
  )
}

/**
 * Change some of a module's fields. The PUT replaces type, binding and data
 * together, so everything else is sent as the cache holds it now.
 */
export function useSaveModule(campaignId: number) {
  return useComposerWrite(
    campaignId,
    'module',
    (composition, id) => cachedOf(composition, 'module', id),
    ({ id, changes }: { id: number; changes: Record<string, unknown> }, module) =>
      read(
        api.PUT('/campaigns/modules/{module_id}', {
          params: { path: { module_id: id }, header: { 'If-Match': module?.updated_at } },
          body: {
            module_type: module?.module_type ?? '',
            content_record_id: module?.content_record_id ?? null,
            decision_slot_id: module?.decision_slot_id ?? null,
            module_data: { ...(module?.module_data ?? {}), ...changes },
          },
        }),
      ),
  )
}

/**
 * Hide or show fields in a module (ADR-187, task-291): the whole list, as the
 * server keeps it, with the module's version. A person's choice only; the
 * server refuses an integration either way.
 */
export function useSetHiddenFields(campaignId: number) {
  return useComposerWrite(
    campaignId,
    'module',
    (composition, id) => cachedOf(composition, 'module', id),
    ({ id, hidden }: { id: number; hidden: string[] }, module) =>
      read(
        api.PUT('/campaigns/modules/{module_id}/hidden-fields', {
          params: { path: { module_id: id }, header: { 'If-Match': module?.updated_at } },
          body: { hidden_fields: hidden },
        }),
      ),
  )
}

export function useMoveModule(campaignId: number) {
  return useComposerWrite(
    campaignId,
    'module',
    (composition, id) => cachedOf(composition, 'module', id),
    ({ id, direction }: { id: number; direction: 'up' | 'down' }, module) =>
      read(
        api.POST('/campaigns/modules/{module_id}/move', {
          params: { path: { module_id: id }, query: { direction }, header: { 'If-Match': module?.updated_at } },
        }),
      ),
  )
}

export function useDeleteModule(campaignId: number) {
  return useComposerWrite(
    campaignId,
    'module',
    (composition, id) => cachedOf(composition, 'module', id),
    async ({ id }: { id: number }, module) => {
      await read(
        api.DELETE('/campaigns/modules/{module_id}', {
          params: { path: { module_id: id }, header: { 'If-Match': module?.updated_at } },
        }),
      )
      return undefined
    },
  )
}

export function useAddModule(campaignId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ variantId, moduleType }: { variantId: number; moduleType: string }) =>
      read(
        api.POST('/campaigns/variants/{variant_id}/modules', {
          params: { path: { variant_id: variantId } },
          body: { module_type: moduleType },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.composition(campaignId) }),
  })
}

/** A new campaign; the server creates its first variant with it. */
export function useCreateCampaign() {
  const queryClient = useQueryClient()
  return useMutation({
    // The generated types make defaulted fields required, so they are stated:
    // a new campaign is a draft, and its first variant takes the name the
    // server would give it anyway.
    mutationFn: (body: { name: string; channel: string }) =>
      read(api.POST('/campaigns/', {
        body: { ...body, status: 'draft', initial_variant_name: 'Variant A' },
      })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.campaigns }),
  })
}

/** A blank variant: secondary to Duplicate, which stays the primary way (VE 5.1). */
export function useCreateVariant(campaignId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; channel: string }) =>
      read(api.POST('/campaigns/{campaign_id}/variants', {
        params: { path: { campaign_id: campaignId } },
        body: { ...body, status: 'draft' },
      })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.composition(campaignId) }),
  })
}

// --- slice 6: catalogue fields and overrides (task-258) ----------------------

export type ContentRecordDetail = components['schemas']['ContentRecordDetail']

/** The unsent campaigns an edit to this record would reach (ADR-178 point 8). */
/** Every field a content record can carry, each with its label (ADR-177 addendum 2026-10-04). */
export function useContentFields() {
  return useQuery({
    queryKey: [...keys.content, 'fields'],
    queryFn: () => read(api.GET('/content/fields')),
    staleTime: Infinity,     // until a page reload or brand switch, as manifests above
  })
}

/**
 * Every campaign whose modules use a record, sent ones included, each with
 * the variants that use it and their stage (task-267). The first page; the
 * screen says when there are more.
 */
export function useCampaignsUsing(recordId: number) {
  return useQuery({
    queryKey: [...keys.contentRecord(recordId), 'campaigns'],
    queryFn: () =>
      read(
        api.GET('/content/{content_id}/campaigns', {
          params: { path: { content_id: recordId }, query: { limit: PAGE_SIZE } },
        }),
      ),
  })
}

export function useContentReach(recordId: number | null | undefined) {
  return useQuery({
    queryKey: [...keys.contentRecord(recordId ?? 0), 'unsent-campaigns'],
    queryFn: () =>
      read(api.GET('/content/{content_id}/unsent-campaigns', { params: { path: { content_id: recordId! } } })),
    enabled: recordId != null,
  })
}

/**
 * Edit one catalogue field of a record (ADR-178 point 1: the default is the
 * catalogue). PATCH with the channel as the field group, so only this
 * channel's fields can be cleared; the record's version is read from the
 * cache when the save is sent and stated in If-Match (task-257), and saves
 * to records run one after another, as the composer's do.
 */
export function useSaveCatalogueField(recordId: number, channel: string) {
  const queryClient = useQueryClient()
  const key = keys.contentRecord(recordId)
  return useMutation({
    scope: { id: 'composer-content' },
    mutationFn: (changes: Record<string, unknown>) =>
      read(
        api.PATCH('/content/{content_id}', {
          params: {
            path: { content_id: recordId },
            header: { 'If-Match': queryClient.getQueryData<ContentRecordDetail>(key)?.updated_at },
          },
          body: { content: changes, groups: [channel] },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  })
}

/**
 * Save part of a record from the record page (task-279): title, description,
 * or one channel's fields. `groups` names the channel whose fields this save
 * may clear, so another channel's copy is never touched (B19). The version is
 * read from the cache when the save is sent and stated in If-Match, and the
 * save joins the composer's catalogue saves in one queue — a save from either
 * page waits for the other, so neither states a version the other just moved.
 */
export function useSaveContentRecord(recordId: number) {
  const queryClient = useQueryClient()
  const key = keys.contentRecord(recordId)
  return useMutation({
    scope: { id: 'composer-content' },
    mutationFn: (body: { title?: string; description?: string; content?: Record<string, unknown>; groups?: string[] }) =>
      read(
        api.PATCH('/content/{content_id}', {
          params: {
            path: { content_id: recordId },
            header: { 'If-Match': queryClient.getQueryData<ContentRecordDetail>(key)?.updated_at },
          },
          body: { content: {}, groups: [], ...body },
        }),
      ),
    // Awaited before the next queued save runs, so it reads the new version.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: key }),
  })
}

/**
 * Create a content record with a title and an optional description only
 * (task-281, Content Write Surface decision 6): nothing else is required at
 * catalogue level (ADR-177 point 4), and the fields are filled on the
 * record's page, where they autosave.
 */
export function useCreateContent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ title, description }: { title: string; description: string }) =>
      read(api.POST('/content/', { body: { title, description: description || null, content: {} } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...keys.content, 'page'] }),
  })
}

/** A record's categories with their scores (task-280), ordered by name. */
export function useContentAssignments(recordId: number) {
  return useQuery({
    queryKey: [...keys.contentRecord(recordId), 'assignments'],
    queryFn: () =>
      read(api.GET('/content/{content_id}/assignments', { params: { path: { content_id: recordId } } })),
  })
}

/**
 * Assign, re-score or remove a record's category (task-280; ADR-080's
 * 2026-10-04 addendum: 1-10, changed in place). Each re-reads the record's
 * assignments, and the content lists, whose category filter they change.
 */
export function useEditAssignments(recordId: number) {
  const queryClient = useQueryClient()
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: [...keys.contentRecord(recordId), 'assignments'] }),
      queryClient.invalidateQueries({ queryKey: [...keys.content, 'page'] }),
      queryClient.invalidateQueries({ queryKey: [...keys.content, 'picker'] }),
    ])
  const path = { content_id: recordId }
  return useMutation({
    scope: { id: `assignments-${recordId}` },
    mutationFn: (
      change:
        | { kind: 'assign'; categoryId: number; score: number }
        | { kind: 'score'; assignmentId: number; score: number }
        | { kind: 'remove'; assignmentId: number },
    ) => {
      if (change.kind === 'assign')
        return read(api.POST('/content/{content_id}/categories', {
          params: { path }, body: { category_id: change.categoryId, score: change.score },
        }))
      if (change.kind === 'score')
        return read(api.PATCH('/content/{content_id}/assignments/{assignment_id}', {
          params: { path: { ...path, assignment_id: change.assignmentId } }, body: { score: change.score },
        }))
      return read(api.DELETE('/content/{content_id}/assignments/{assignment_id}', {
        params: { path: { ...path, assignment_id: change.assignmentId } },
      }))
    },
    // Re-read after a refusal too: a 409 means somebody assigned it meanwhile,
    // and the list should show what is there now.
    onSettled: refresh,
  })
}

/** A record's published versions, newest first (ADR-128): what each send used. */
export function useContentVersions(recordId: number) {
  return useQuery({
    queryKey: [...keys.contentRecord(recordId), 'versions'],
    queryFn: () =>
      read(api.GET('/content/{content_record_id}/versions', { params: { path: { content_record_id: recordId } } })),
  })
}

/**
 * Activate or deactivate. The route takes no version token but moves the
 * record's `updated_at`, so the record is re-read afterwards — otherwise the
 * next field save would state the old version and be refused as somebody
 * else's change (task-279).
 */
export function useSetContentStatus(recordId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    scope: { id: 'composer-content' },
    mutationFn: (status: 'active' | 'inactive') =>
      read(api.PUT('/content/{content_id}/status', { params: { path: { content_id: recordId } }, body: { status } })),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: keys.contentRecord(recordId) }),
        queryClient.invalidateQueries({ queryKey: [...keys.content, 'page'] }),
      ]),
  })
}

/**
 * Mark or unmark a record ready for a channel (ADR-174, task-285). A mark is
 * its own row and moves no version, but who marked it, when, and the server's
 * warning come with the record, so the record is re-read — after a refusal
 * too, so the switch shows what is stored. In the record's write queue, so a
 * mark lands after a field save in flight and its warning reads that save.
 */
export function useMarkReady(recordId: number, channel: string) {
  const queryClient = useQueryClient()
  const path = { content_id: recordId, channel }
  return useMutation({
    scope: { id: 'composer-content' },
    mutationFn: (ready: boolean) =>
      ready
        ? read(api.PUT('/content/{content_id}/readiness/{channel}', { params: { path } }))
        : read(api.DELETE('/content/{content_id}/readiness/{channel}', { params: { path } })),
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: keys.contentRecord(recordId) }),
        queryClient.invalidateQueries({ queryKey: [...keys.content, 'page'] }),
        queryClient.invalidateQueries({ queryKey: [...keys.content, 'picker'] }),
      ]),
  })
}

/**
 * Turn machine ready on or off (ADR-179 point 2; people only). A column on the
 * record, so it moves the version as status does, and the record is re-read
 * for the next field save to state the new one.
 */
export function useSetMachineReady(recordId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    scope: { id: 'composer-content' },
    mutationFn: (machineReady: boolean) =>
      read(api.PUT('/content/{content_id}/machine-ready', {
        params: { path: { content_id: recordId } }, body: { machine_ready: machineReady },
      })),
    onSettled: () => queryClient.invalidateQueries({ queryKey: keys.contentRecord(recordId) }),
  })
}

/** The brands this person may copy the record into (task-50). */
export function useDuplicateTargets(recordId: number) {
  return useQuery({
    queryKey: [...keys.contentRecord(recordId), 'duplicate-targets'],
    queryFn: () =>
      read(api.GET('/content/{content_id}/duplicate-targets', { params: { path: { content_id: recordId } } })),
  })
}

/** Copy the record into a brand. The copy has no published version. */
export function useDuplicateContent(recordId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (targetBrandId: number) =>
      read(
        api.POST('/content/{content_id}/duplicate', {
          params: { path: { content_id: recordId } },
          body: { target_brand_id: targetBrandId },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [...keys.content, 'page'] }),
  })
}

/** Publish the record's current content, which is what sends then use (D5). */
export function usePublishRecord(recordId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => read(api.POST('/content/versions', { body: { content_record_id: recordId } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.contentRecord(recordId) }),
  })
}

/**
 * Change a module's override (task-256): fields to set, fields to drop, and
 * optionally the reason. The whole set is built from the override **as the
 * cache holds it when the save is sent**, and the module's version goes in
 * If-Match — the same queue as every other module write, because an override
 * write moves the module's version.
 */
export function useSetOverride(campaignId: number) {
  return useComposerWrite(
    campaignId,
    'module',
    (composition, id) => cachedOf(composition, 'module', id),
    (
      { id, set = {}, unset = [], reason }: {
        id: number
        set?: Record<string, unknown>
        unset?: string[]
        reason?: string | null
      },
      module,
    ) => {
      const current = { ...(module?.active_override?.field_overrides ?? {}), ...set }
      for (const field of unset) delete current[field]
      return read(
        api.PUT('/overrides/modules/{module_id}', {
          params: { path: { module_id: id }, header: { 'If-Match': module?.updated_at } },
          body: {
            field_overrides: current,
            reason: reason === undefined ? (module?.active_override?.reason ?? null) : reason,
          },
        }),
      )
    },
  )
}

/** Bind a catalogue module to a record (or rebind it). */
export function useBindModule(campaignId: number) {
  return useComposerWrite(
    campaignId,
    'module',
    (composition, id) => cachedOf(composition, 'module', id),
    ({ id, contentRecordId }: { id: number; contentRecordId: number }, module) =>
      read(
        api.PUT('/campaigns/modules/{module_id}', {
          params: { path: { module_id: id }, header: { 'If-Match': module?.updated_at } },
          body: {
            module_type: module?.module_type ?? '',
            content_record_id: contentRecordId,
            decision_slot_id: null,
            module_data: module?.module_data ?? {},
          },
        }),
      ),
  )
}

// --- slice 7: decision slots on their modules (task-264) ---------------------

export type StrategyMeta = components['schemas']['StrategyMeta']
export type Category = components['schemas']['Category']
type SlotStats = components['schemas']['DecisionSlotStats']

/** The registered decision strategies, each with the settings it declares. */
export function useStrategies() {
  return useQuery({
    queryKey: ['decision', 'strategies'],
    queryFn: () => read(api.GET('/decision/strategies')),
    staleTime: Infinity,     // until a page reload or brand switch, as manifests above
  })
}

/** The category taxonomy, shared across brands (it has no brand column). */
export function useCategories() {
  return useQuery({
    queryKey: ['content', 'categories'],
    queryFn: () => read(api.GET('/content/categories')),
  })
}

export type CategoryRelation = components['schemas']['CategoryRelation']

/** The parent -> child edges of the taxonomy, so a picker can show its hierarchy. */
export function useCategoryRelations() {
  return useQuery({
    queryKey: ['content', 'category-relations'],
    queryFn: () => read(api.GET('/content/category-relations')),
  })
}

/** How many records the bind picker lists at once; narrowing finds the rest. */
export const PICKER_SIZE = 20

/**
 * The bind picker's records (task-269): active ones, by title or description
 * and optionally one category, which the server orders by score (ADR-175
 * addendum 2026-10-04). The previous list stays up while the next one loads,
 * so the rows do not blink away on every pause in typing. `readyFor` narrows
 * to records marked ready for that channel (task-286); null lists them all.
 */
export function usePickerRecords(q: string, categoryId: number | null, readyFor: string | null = null) {
  return useQuery({
    queryKey: [...keys.content, 'picker', q, categoryId, readyFor],
    queryFn: () =>
      read(
        api.GET('/content/', {
          params: {
            query: {
              limit: PICKER_SIZE,
              q: q || undefined,
              status: 'active',
              category_id: categoryId ?? undefined,
              ready_for: readyFor ?? undefined,
            },
          },
        }),
      ),
    placeholderData: (previous) => previous,
  })
}

/** Fill a catalogue module from a new slot, in one write with the module's version. */
export function useAttachSlot(campaignId: number) {
  return useComposerWrite(
    campaignId,
    'module',
    (composition, id) => cachedOf(composition, 'module', id),
    ({ id, strategy }: { id: number; strategy?: string }, module) =>
      read(
        api.POST('/campaigns/modules/{module_id}/decision-slot', {
          params: { path: { module_id: id }, header: { 'If-Match': module?.updated_at } },
          body: { decision_strategy: strategy ?? 'top_score' },
        }),
      ),
  )
}

/**
 * Change some of a slot's settings: PATCH leaves a section it is not sent
 * as stored (inventory B16). The slot's version is read from the cached slot
 * read when the save is sent, and slot saves run one after another, as the
 * composer's other writes do.
 */
export function useSaveSlot(campaignId: number, slotId: number) {
  const queryClient = useQueryClient()
  const statsKey = [...keys.decisionSlot(slotId), 'stats']
  return useMutation({
    scope: { id: 'composer-slot' },
    mutationFn: (changes: {
      decision_strategy?: string
      candidate_filter?: Record<string, unknown>
      strategy_config?: Record<string, unknown>
    }) =>
      read(
        api.PATCH('/campaigns/decision-slots/{slot_id}', {
          params: {
            path: { slot_id: slotId },
            header: { 'If-Match': queryClient.getQueryData<SlotStats>(statsKey)?.slot.updated_at },
          },
          body: changes,
        }),
      ),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: keys.decisionSlot(slotId) }),
        queryClient.invalidateQueries({ queryKey: keys.composition(campaignId) }),
      ]),
  })
}

// --- the preview overlay (task-265) ------------------------------------------

export type RenderedVariant = components['schemas']['RenderedVariant']
export type ModuleState = components['schemas']['ModuleState']

/**
 * The variant rendered as it is saved now, with each module's state
 * (task-227). `stamp` is the composition's update time, so every save —
 * which re-reads the composition — re-renders too: the preview never needs
 * a render button (Variant Editor interview 2.1).
 */
export function useRenderedVariant(variantId: number, recipientId: number | null, stamp: number) {
  return useQuery({
    queryKey: ['render', variantId, recipientId, stamp],
    queryFn: () =>
      read(
        api.GET('/rendering/variants/{variant_id}', {
          params: { path: { variant_id: variantId }, query: { recipient_id: recipientId ?? undefined } },
        }),
      ),
    placeholderData: (previous) => previous,
  })
}

/** Recipients found by identifier or address, for naming one in a preview. */
export function useRecipientSearch(q: string) {
  return useQuery({
    queryKey: ['recipients', 'search', q],
    queryFn: () => read(api.GET('/recipients/', { params: { query: { q, limit: 10 } } })),
    enabled: q.trim().length > 0,
  })
}

// --- the advisory fence (task-254) -------------------------------------------

export type VariantFence = components['schemas']['VariantFence']

/** Unblock a variant: a person may clear any fence (ADR-180 point 1). */
export function useUnblock(campaignId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (variantId: number) =>
      read(api.DELETE('/campaigns/variants/{variant_id}/fence', { params: { path: { variant_id: variantId } } })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: keys.composition(campaignId) }),
  })
}

// --- brand profiles (task-350, ADR-194) -------------------------------------

export type BrandProfile = components['schemas']['BrandProfile']
export type BrandProfileSummary = components['schemas']['BrandProfileSummary']
export type ProfileField = components['schemas']['ProfileFieldOut']

/** The fields a profile may hold, as this installation's setup file declares them. */
export function useBrandProfileStructure() {
  return useQuery({
    queryKey: keys.brandProfileStructure,
    queryFn: () => read(api.GET('/brand-profiles/structure')),
    staleTime: Infinity,
  })
}

/** The working brand's profiles, the default first, then by name. */
export function useBrandProfiles(offset = 0) {
  return useQuery({
    queryKey: [...keys.brandProfiles, 'page', offset],
    queryFn: () => read(api.GET('/brand-profiles/', { params: { query: { limit: PAGE_SIZE, offset } } })),
  })
}

/**
 * Every profile of the brand, for the variant editor's choice. One page of the
 * largest size: a brand with more than 200 looks is not a case worth paging a
 * dropdown for, and the list says when it was cut.
 */
export function useBrandProfileChoices() {
  return useQuery({
    queryKey: [...keys.brandProfiles, 'choices'],
    queryFn: () => read(api.GET('/brand-profiles/', { params: { query: { limit: 200, offset: 0 } } })),
  })
}

export function useBrandProfile(id: number) {
  return useQuery({
    queryKey: keys.brandProfile(id),
    queryFn: () => read(api.GET('/brand-profiles/{profile_id}', { params: { path: { profile_id: id } } })),
  })
}

/** After any profile write: the list, the choices and the editor's composition. */
function useProfileRefresh() {
  const queryClient = useQueryClient()
  return (profile?: BrandProfile) => {
    if (profile) queryClient.setQueryData(keys.brandProfile(profile.id), profile)
    void queryClient.invalidateQueries({ queryKey: keys.brandProfiles, predicate: (q) => q.queryKey[1] !== profile?.id })
    // A variant shows its profile's name and what it misses.
    void queryClient.invalidateQueries({ queryKey: keys.campaigns, predicate: (q) => q.queryKey[2] === 'composition' })
  }
}

export function useCreateBrandProfile() {
  const refresh = useProfileRefresh()
  return useMutation({
    // New profiles start English and marketing; transactional waits for task-355.
    mutationFn: ({ name }: { name: string }) =>
      read(api.POST('/brand-profiles/', { body: { name, language: 'en', kind: 'marketing' } })),
    onSuccess: (profile) => refresh(profile),
  })
}

/** Replace the name and values, stating the version that was read (If-Match). */
/**
 * Replace the name and values. `version` is the `updated_at` the editor's
 * draft started from, **not** whatever the cache holds now: a background
 * refresh may already have brought somebody else's newer version, and sending
 * that would overwrite their change unseen instead of being refused (Codex
 * doc-14).
 */
export function useSaveBrandProfile(id: number) {
  const refresh = useProfileRefresh()
  return useMutation({
    scope: { id: `brand-profile-${id}` },
    mutationFn: ({
      version,
      ...body
    }: {
      version: string
      name: string
      language: string
      field_values: Record<string, unknown>
    }) =>
      read(
        api.PUT('/brand-profiles/{profile_id}', {
          params: { path: { profile_id: id }, header: { 'If-Match': version } },
          body,
        }),
      ),
    onSuccess: (profile) => refresh(profile),
  })
}

export function useDuplicateBrandProfile(id: number) {
  const refresh = useProfileRefresh()
  return useMutation({
    mutationFn: () => read(api.POST('/brand-profiles/{profile_id}/duplicate', { params: { path: { profile_id: id } } })),
    onSuccess: (profile) => refresh(profile),
  })
}

export function useMakeDefaultBrandProfile(id: number) {
  const queryClient = useQueryClient()
  const refresh = useProfileRefresh()
  return useMutation({
    mutationFn: () =>
      read(api.POST('/brand-profiles/{profile_id}/make-default', { params: { path: { profile_id: id } } })),
    // The old default changed too, so every cached profile is re-read.
    onSuccess: (profile) => {
      refresh(profile)
      return queryClient.invalidateQueries({ queryKey: keys.brandProfiles })
    },
  })
}

/** Delete a profile; the variants using it move to the default (with a notice). */
export function useDeleteBrandProfile(id: number) {
  const queryClient = useQueryClient()
  const refresh = useProfileRefresh()
  return useMutation({
    mutationFn: () =>
      read(
        api.DELETE('/brand-profiles/{profile_id}', {
          params: {
            path: { profile_id: id },
            header: { 'If-Match': queryClient.getQueryData<BrandProfile>(keys.brandProfile(id))?.updated_at },
          },
        }),
      ),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: keys.brandProfile(id) })
      refresh()
    },
  })
}

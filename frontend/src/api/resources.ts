import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

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
async function read<T>(call: Promise<{ data?: T; response: Response }>): Promise<T> {
  const result = await call
  if (!result.response.ok) throw new HttpError(result.response.status)
  return result.data as T
}

export function useCampaigns() {
  return useQuery({
    queryKey: keys.campaigns,
    queryFn: () => read(api.GET('/campaigns/')),
  })
}

export function useContentList() {
  return useQuery({
    queryKey: keys.content,
    queryFn: () => read(api.GET('/content/')),
  })
}

export function useContentRecord(id: number) {
  return useQuery({
    queryKey: keys.contentRecord(id),
    queryFn: () =>
      read(api.GET('/content/{content_id}', { params: { path: { content_id: id } } })),
  })
}

export function useAudienceGroups() {
  return useQuery({
    queryKey: keys.audienceGroups,
    queryFn: () => read(api.GET('/api/audience-groups/')),
  })
}

export function useAudienceGroup(id: number) {
  return useQuery({
    queryKey: keys.audienceGroup(id),
    queryFn: () =>
      read(api.GET('/api/audience-groups/{group_id}', { params: { path: { group_id: id } } })),
  })
}

export function useApprovals() {
  return useQuery({
    queryKey: keys.approvals,
    queryFn: () => read(api.GET('/approvals/')),
  })
}

export function useApproval(id: number) {
  return useQuery({
    queryKey: keys.approval(id),
    queryFn: () =>
      read(api.GET('/approvals/{pending_id}', { params: { path: { pending_id: id } } })),
  })
}

/**
 * The first page of sends, newest first -- the server's default of 50.
 *
 * No pager yet: one standard pagination mechanism is task-88's to build, and a
 * screen-local one would be the second answer it exists to prevent.
 */
export function useDeliveries() {
  return useQuery({
    queryKey: keys.deliveries,
    queryFn: () => read(api.GET('/delivery/send-instances')),
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

export function useDeliveryExecutions(id: number) {
  return useQuery({
    queryKey: keys.deliveryExecutions(id),
    queryFn: () =>
      read(
        api.GET('/delivery/send-instances/{send_instance_id}/executions', {
          params: { path: { send_instance_id: id } },
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

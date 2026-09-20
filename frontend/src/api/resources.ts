import { useQuery } from '@tanstack/react-query'

import { api } from './client'
import { HttpError } from './session'
import type { components } from './schema'

export type Campaign = components['schemas']['Campaign']
export type ContentRecord = components['schemas']['ContentRecord']
export type AudienceGroup = components['schemas']['AudienceGroup']
export type PendingActionRow = components['schemas']['PendingActionRow']
export type PendingActionDetail = components['schemas']['PendingActionDetail']

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
  content: ['content'] as const,
  contentRecord: (id: number) => ['content', id] as const,
  audienceGroups: ['audience-groups'] as const,
  audienceGroup: (id: number) => ['audience-groups', id] as const,
  approvals: ['approvals'] as const,
  approval: (id: number) => ['approvals', id] as const,
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

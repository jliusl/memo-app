import { request } from './client'

export type Memo = {
  id: number
  title: string | null
  body: string
  pinned: boolean
  created_at: string
  updated_at: string
}

export type MemoDraft = {
  title: string | null
  body: string
}

/** The API returns memos already ordered - pinned first, then most recently edited - so
 * the list renders the response as it arrives and never sorts on the client. */
export const listMemos = (query: string): Promise<Memo[]> => {
  const search = new URLSearchParams({ limit: '200' })
  if (query.trim() !== '') {
    search.set('q', query.trim())
  }
  return request<Memo[]>(`/api/memos?${search.toString()}`)
}

export const createMemo = (draft: MemoDraft): Promise<Memo> =>
  request<Memo>('/api/memos', { method: 'POST', body: JSON.stringify({ ...draft, pinned: false }) })

export const updateMemo = (id: number, changes: Partial<MemoDraft & { pinned: boolean }>): Promise<Memo> =>
  request<Memo>(`/api/memos/${id}`, { method: 'PATCH', body: JSON.stringify(changes) })

export const deleteMemo = (id: number): Promise<void> =>
  request<void>(`/api/memos/${id}`, { method: 'DELETE' })

/**
 * What to call a memo on screen. A memo written before it was titled still has to be
 * nameable - in the list, and in the accessible name of its own buttons - so the first
 * line of the body stands in. The API rejects a memo with neither, so this cannot be blank.
 */
export function displayTitle(memo: Memo): string {
  if (memo.title !== null && memo.title !== '') {
    return memo.title
  }

  const firstLine = memo.body
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line !== '')

  return firstLine ?? 'Untitled'
}

/** Empty inputs mean "no value", which is what the API expects for a cleared title. */
export function toDraft(title: string, body: string): MemoDraft {
  const trimmed = title.trim()
  return { title: trimmed === '' ? null : trimmed, body }
}

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { deleteMemo, displayTitle, toDraft, updateMemo } from '../api/memos'
import type { Memo, MemoDraft } from '../api/memos'

const MEMOS_QUERY_KEY = ['memos']

type Props = {
  memo: Memo
}

export function MemoItem({ memo }: Props) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const name = displayTitle(memo)
  const titleId = `memo-title-${memo.id}`

  const refresh = () => queryClient.invalidateQueries({ queryKey: MEMOS_QUERY_KEY })

  const pin = useMutation({
    mutationFn: () => updateMemo(memo.id, { pinned: !memo.pinned }),
    onSuccess: refresh,
  })

  const save = useMutation({
    mutationFn: (draft: MemoDraft) => updateMemo(memo.id, draft),
    onSuccess: () => {
      setEditing(false)
      void refresh()
    },
  })

  const remove = useMutation({ mutationFn: () => deleteMemo(memo.id), onSuccess: refresh })

  return (
    <li className="rounded border border-slate-200 bg-white p-4">
      <article aria-labelledby={titleId} className="flex flex-col gap-2">
        <h2 id={titleId} className="text-lg font-semibold text-slate-900">
          {name}
          {memo.pinned && (
            <span className="ml-2 rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
              Pinned
            </span>
          )}
        </h2>

        {editing ? (
          <MemoEditForm
            memo={memo}
            name={name}
            pending={save.isPending}
            onSubmit={(draft) => save.mutate(draft)}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <>
            {memo.title === null && (
              <p className="text-xs text-slate-500">Untitled, so the first line stands in for it.</p>
            )}
            {memo.body !== '' && <p className="whitespace-pre-wrap text-slate-800">{memo.body}</p>}
            <p className="text-xs text-slate-500">
              Edited <time dateTime={memo.updated_at}>{formatTimestamp(memo.updated_at)}</time>
            </p>

            <div className="flex gap-2">
              <ActionButton
                label={`${memo.pinned ? 'Unpin' : 'Pin'} ${name}`}
                pressed={memo.pinned}
                onClick={() => pin.mutate()}
              >
                {memo.pinned ? 'Unpin' : 'Pin'}
              </ActionButton>
              <ActionButton label={`Edit ${name}`} onClick={() => setEditing(true)}>
                Edit
              </ActionButton>
              <ActionButton
                label={`Delete ${name}`}
                onClick={() => {
                  // Permanent, with no recycle bin behind it - so ask once, by name.
                  if (window.confirm(`Delete "${name}"? This cannot be undone.`)) {
                    remove.mutate()
                  }
                }}
              >
                Delete
              </ActionButton>
            </div>
          </>
        )}
      </article>
    </li>
  )
}

type ActionButtonProps = {
  label: string
  pressed?: boolean
  onClick: () => void
  children: string
}

/**
 * Each button's visible text is short and repeats across the list, so its accessible name
 * is the memo it belongs to: "Delete Groceries" rather than a fourth identical "Delete".
 */
function ActionButton({ label, pressed, onClick, children }: ActionButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={pressed}
      onClick={onClick}
      className="rounded border border-slate-300 px-3 py-1 text-sm text-slate-800"
    >
      {children}
    </button>
  )
}

type EditFormProps = {
  memo: Memo
  name: string
  pending: boolean
  onSubmit: (draft: MemoDraft) => void
  onCancel: () => void
}

function MemoEditForm({ memo, name, pending, onSubmit, onCancel }: EditFormProps) {
  const [title, setTitle] = useState(memo.title ?? '')
  const [body, setBody] = useState(memo.body)

  return (
    <form
      aria-label={`Edit ${name}`}
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit(toDraft(title, body))
      }}
    >
      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Title
        <input
          name="title"
          maxLength={200}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          className="rounded border border-slate-300 px-3 py-2 font-normal text-slate-900"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Body
        <textarea
          name="body"
          rows={3}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          className="rounded border border-slate-300 px-3 py-2 font-normal text-slate-900"
        />
      </label>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={pending}
          className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
        >
          Save
        </button>
        <button type="button" onClick={onCancel} className="rounded border border-slate-300 px-4 py-2 text-sm">
          Cancel
        </button>
      </div>
    </form>
  )
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString()
}

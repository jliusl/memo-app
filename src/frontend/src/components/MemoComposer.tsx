import { useState } from 'react'

import { toDraft } from '../api/memos'
import type { MemoDraft } from '../api/memos'

type Props = {
  pending: boolean
  error: string | null
  onSubmit: (draft: MemoDraft) => void
}

/**
 * The form's accessible name is what keeps its "Title" and "Body" fields tellable apart
 * from the ones in a memo being edited, which may be on screen at the same time. Tests
 * scope to it the same way anyone using a screen reader would.
 */
export function MemoComposer({ pending, error, onSubmit }: Props) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')

  return (
    <form
      aria-label="New memo"
      className="flex flex-col gap-3 rounded border border-slate-200 bg-white p-4"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit(toDraft(title, body))
        setTitle('')
        setBody('')
      }}
    >
      {error !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

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

      <button
        type="submit"
        // A memo needs a title or a body. Saying so by disabling the button beats letting
        // the request go out only to come back as a validation error.
        disabled={pending || (title.trim() === '' && body.trim() === '')}
        className="self-start rounded bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
      >
        Add memo
      </button>
    </form>
  )
}

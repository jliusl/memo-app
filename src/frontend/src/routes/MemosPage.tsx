import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { logOut } from '../api/auth'
import { createMemo, listMemos } from '../api/memos'
import { useSession } from '../auth/session'
import { MemoComposer } from '../components/MemoComposer'
import { MemoItem } from '../components/MemoItem'

export function MemosPage() {
  const session = useSession()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  // The search text is part of the key, so results for one query can never be shown under
  // another while the new response is in flight.
  const memos = useQuery({ queryKey: ['memos', query], queryFn: () => listMemos(query) })

  const add = useMutation({
    mutationFn: createMemo,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['memos'] }),
  })

  const signOut = useMutation({
    mutationFn: logOut,
    onSuccess: () => {
      // Dropping every cached query is what makes signing out complete: no memo from the
      // previous session can be rendered again, not even for a frame.
      queryClient.clear()
      // And leave the page explicitly. Clearing the cache is not a notification: it used to
      // be left to RequireAuth noticing that the session query had failed, which worked
      // only while its observer happened to hear about it. When it did not, the user stayed
      // on the memo list with a 401 rendered in place of their Memos.
      navigate('/sign-in', { replace: true })
    },
  })

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-2xl flex-col gap-6 p-6">
      <header className="flex items-baseline justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Memos</h1>
          {session.data !== undefined && (
            <p className="text-sm text-slate-600">
              Signed in as <span className="font-medium">{session.data.email}</span>
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => signOut.mutate()}
          className="rounded border border-slate-300 px-3 py-1 text-sm text-slate-800"
        >
          Sign out
        </button>
      </header>

      <form role="search" aria-label="Search memos" onSubmit={(event) => event.preventDefault()}>
        <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
          Search memos
          {/* type="search" gives the field the `searchbox` role. */}
          <input
            type="search"
            name="q"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="rounded border border-slate-300 px-3 py-2 font-normal text-slate-900"
          />
        </label>
      </form>

      <MemoComposer
        pending={add.isPending}
        error={add.isError ? add.error.message : null}
        onSubmit={(draft) => add.mutate(draft)}
      />

      {memos.isPending && <p role="status">Loading your memos…</p>}

      {memos.isError && <p role="alert">Could not load your memos: {memos.error.message}</p>}

      {memos.isSuccess &&
        (memos.data.length === 0 ? (
          <p className="text-slate-600">
            {query.trim() === '' ? 'No memos yet. Write one above.' : `No memos match "${query.trim()}".`}
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {memos.data.map((memo) => (
              <MemoItem key={memo.id} memo={memo} />
            ))}
          </ul>
        ))}
    </main>
  )
}

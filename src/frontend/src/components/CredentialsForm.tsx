import { useId, useState } from 'react'

import type { Credentials } from '../api/auth'

type Props = {
  heading: string
  submitLabel: string
  pending: boolean
  error: string | null
  passwordAutoComplete: 'current-password' | 'new-password'
  passwordMinLength?: number
  onSubmit: (credentials: Credentials) => void
}

/**
 * Signing in and registering ask for the same two things, so they share one form. Each
 * input is wrapped in its own label rather than tied to one by `htmlFor` + a generated id:
 * that is fewer moving parts, and it makes the field's accessible name its visible text.
 */
export function CredentialsForm({
  heading,
  submitLabel,
  pending,
  error,
  passwordAutoComplete,
  passwordMinLength,
  onSubmit,
}: Props) {
  const headingId = useId()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  return (
    <form
      aria-labelledby={headingId}
      className="mx-auto flex w-full max-w-sm flex-col gap-4 p-6"
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit({ email, password })
      }}
    >
      <h1 id={headingId} className="text-2xl font-semibold text-slate-900">
        {heading}
      </h1>

      {error !== null && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Email
        <input
          type="email"
          name="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="rounded border border-slate-300 px-3 py-2 font-normal text-slate-900"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm font-medium text-slate-700">
        Password
        <input
          type="password"
          name="password"
          autoComplete={passwordAutoComplete}
          required
          minLength={passwordMinLength}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="rounded border border-slate-300 px-3 py-2 font-normal text-slate-900"
        />
      </label>

      <button
        type="submit"
        disabled={pending}
        className="rounded bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
      >
        {submitLabel}
      </button>
    </form>
  )
}

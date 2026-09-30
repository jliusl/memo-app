import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'

import { ApiError } from '../api/client'
import { useSession } from './session'

export function RequireAuth({ children }: { children: ReactNode }) {
  const session = useSession()

  if (session.isPending) {
    return <p role="status">Checking your session…</p>
  }

  if (session.isError) {
    // Only a 401 means "signed out". Anything else - the API being down, a 500 - is a real
    // failure, and redirecting to the sign-in form would hide it behind a form that cannot
    // possibly work.
    if (session.error instanceof ApiError && session.error.status === 401) {
      return <Navigate to="/sign-in" replace />
    }
    return <p role="alert">Could not reach the API: {session.error.message}</p>
  }

  return <>{children}</>
}

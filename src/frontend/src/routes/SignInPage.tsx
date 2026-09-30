import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { logIn } from '../api/auth'
import { SESSION_QUERY_KEY } from '../auth/session'
import { CredentialsForm } from '../components/CredentialsForm'

export function SignInPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: logIn,
    onSuccess: (user) => {
      // The response already is the session, so seeding the cache skips a round trip to
      // /me that would otherwise flash the "checking your session" state.
      queryClient.setQueryData(SESSION_QUERY_KEY, user)
      navigate('/', { replace: true })
    },
  })

  return (
    <main className="flex min-h-screen flex-col justify-center bg-slate-50">
      <CredentialsForm
        heading="Sign in"
        submitLabel="Sign in"
        passwordAutoComplete="current-password"
        pending={mutation.isPending}
        error={mutation.isError ? mutation.error.message : null}
        onSubmit={(credentials) => mutation.mutate(credentials)}
      />
      <p className="text-center text-sm text-slate-700">
        No account yet?{' '}
        <Link to="/register" className="font-medium underline">
          Create one
        </Link>
      </p>
    </main>
  )
}

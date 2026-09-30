import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { register } from '../api/auth'
import { SESSION_QUERY_KEY } from '../auth/session'
import { CredentialsForm } from '../components/CredentialsForm'

/** Matches the server's rule. Stated once here so the browser can catch it before the
 * round trip; the server still enforces it, because this is only a convenience. */
const PASSWORD_MIN_LENGTH = 8

export function RegisterPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const mutation = useMutation({
    mutationFn: register,
    onSuccess: (user) => {
      // Registering signs you in - the response carries the session cookie - so this is
      // the same hand-off as the sign-in page rather than a separate "now go and log in".
      queryClient.setQueryData(SESSION_QUERY_KEY, user)
      navigate('/', { replace: true })
    },
  })

  return (
    <main className="flex min-h-screen flex-col justify-center bg-slate-50">
      <CredentialsForm
        heading="Create account"
        submitLabel="Create account"
        passwordAutoComplete="new-password"
        passwordMinLength={PASSWORD_MIN_LENGTH}
        pending={mutation.isPending}
        error={mutation.isError ? mutation.error.message : null}
        onSubmit={(credentials) => mutation.mutate(credentials)}
      />
      <p className="text-center text-sm text-slate-700">
        Already have an account?{' '}
        <Link to="/sign-in" className="font-medium underline">
          Sign in
        </Link>
      </p>
    </main>
  )
}

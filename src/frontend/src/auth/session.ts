import { useQuery } from '@tanstack/react-query'

import { getCurrentUser } from '../api/auth'

/** Also the cache key that a successful sign-in writes into, so the app never has to
 * fetch /me a second time just to learn what it already knows. */
export const SESSION_QUERY_KEY = ['session']

export function useSession() {
  return useQuery({ queryKey: SESSION_QUERY_KEY, queryFn: getCurrentUser })
}

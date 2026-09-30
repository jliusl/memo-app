/** An error response from the API. The status is kept because callers branch on it:
 * a 401 means "signed out" while a 409 means "that email is taken". */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type ValidationItem = { msg?: unknown }

/** FastAPI reports `detail` either as a string (HTTPException) or as a list of validation
 * errors. Flatten both into one line, because every caller only has somewhere to show one. */
function describe(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    const messages = (detail as ValidationItem[])
      .map((item) => item.msg)
      .filter((msg): msg is string => typeof msg === 'string')
    if (messages.length > 0) {
      return messages.join('; ')
    }
  }

  return `Request failed with status ${status}`
}

/**
 * The single place a request is made, so that credentials and error handling cannot be
 * forgotten on one endpoint. Paths are relative: the dev and preview servers proxy /api,
 * which is what makes the session cookie a first-party cookie.
 */
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: 'same-origin',
    headers: init.body === undefined ? init.headers : { 'Content-Type': 'application/json', ...init.headers },
  })

  if (!response.ok) {
    // A failed response is not guaranteed to be JSON, so a parse failure must not replace
    // the status code with a confusing syntax error.
    const body: unknown = await response.json().catch(() => null)
    throw new ApiError(response.status, describe(response.status, body))
  }

  // 204 has no body to parse, and deleting a memo answers with one.
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
}

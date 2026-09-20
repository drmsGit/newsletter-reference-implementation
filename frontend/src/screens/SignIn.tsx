import { useState } from 'react'
import { Button, FieldError, Form, Input, Label, TextField } from 'react-aria-components'
import { Navigate, useNavigate } from 'react-router'

import { useRequestCode, useSession, useVerifyCode } from '../api/session'
import { PRODUCT_NAME } from '../branding'

/**
 * Signing in, in two steps: ask for a code, then submit it.
 *
 * One component rather than two routes, because the second step is meaningless
 * without the first and a URL for it would be a URL that cannot be bookmarked.
 */
export default function SignIn() {
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [codeRequested, setCodeRequested] = useState(false)

  const navigate = useNavigate()
  const session = useSession()
  const requestCode = useRequestCode()
  const verifyCode = useVerifyCode()

  /**
   * Somebody who already has a session has no business on this screen.
   *
   * This also covers the case the screen is reached by typing the URL, not
   * only by being redirected here -- the guard sends people in, and nothing
   * but this sends them back out.
   */
  if (session.data) return <Navigate to="/" replace />

  return (
    <main className="signin">
      <h1>{PRODUCT_NAME}</h1>

      {!codeRequested ? (
        <Form
          onSubmit={(event) => {
            event.preventDefault()
            requestCode.mutate(email, { onSuccess: () => setCodeRequested(true) })
          }}
        >
          <TextField name="email" type="email" isRequired value={email} onChange={setEmail}>
            <Label>Email address</Label>
            <Input autoFocus autoComplete="email" />
            <FieldError />
          </TextField>
          <Button type="submit" isDisabled={requestCode.isPending}>
            {requestCode.isPending ? 'Sending…' : 'Send me a code'}
          </Button>
        </Form>
      ) : (
        <Form
          onSubmit={(event) => {
            event.preventDefault()
            /**
             * **Navigating on success is not cosmetic.**
             *
             * Verifying sets the session cookie, so the application is signed
             * in the moment this resolves -- but this screen is a route, and a
             * route does not change because some state elsewhere did. Without
             * this the user submits a correct code, the request returns 200,
             * and the sign-in form simply sits there: no error, no movement,
             * nothing to retry. Found by driving the real app on 2026-09-20;
             * the unit tests asserted both steps and neither asserted the
             * outcome.
             */
            verifyCode.mutate(
              { email, code },
              { onSuccess: () => void navigate('/', { replace: true }) },
            )
          }}
        >
          {/*
            **This wording is load-bearing and must stay conditional-free.**

            The request route answers 202 identically for a known address, an
            unknown one, a deactivated account and a failed send -- ADR-151 §2.
            Saying "check your inbox" for one and "no such account" for another
            would rebuild, in the interface, exactly the account-enumeration
            oracle the backend spends a uniform response to close. So this says
            "if that address belongs to an account", and says it every time.
          */}
          <p>
            If that address belongs to an active account, a sign-in code is on its
            way. Enter it below.
          </p>
          <TextField name="code" isRequired value={code} onChange={setCode}>
            <Label>Sign-in code</Label>
            <Input autoFocus inputMode="numeric" autoComplete="one-time-code" />
            <FieldError />
          </TextField>
          <Button type="submit" isDisabled={verifyCode.isPending}>
            {verifyCode.isPending ? 'Checking…' : 'Sign in'}
          </Button>
          {verifyCode.isError && (
            <p role="alert" className="error">
              That code is not valid or has expired.
            </p>
          )}
          <Button type="button" onPress={() => setCodeRequested(false)}>
            Use a different address
          </Button>
        </Form>
      )}
    </main>
  )
}

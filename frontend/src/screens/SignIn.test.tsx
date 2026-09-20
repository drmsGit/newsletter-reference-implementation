import { fireEvent, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Route, Routes } from 'react-router'

import SignIn from './SignIn'
import { A_SESSION, jsonResponse, renderWithProviders, stubFetch } from '../test-utils'

afterEach(() => vi.unstubAllGlobals())

describe('signing in', () => {
  it('asks for an email address first', () => {
    stubFetch({
      'GET /auth/session': () => jsonResponse({ detail: 'Authentication required' }, 401),
    })
    renderWithProviders(<SignIn />)

    expect(screen.getByLabelText('Email address')).toBeInTheDocument()
    expect(screen.queryByLabelText('Sign-in code')).not.toBeInTheDocument()
  })

  it('moves to the code step once a code has been requested', async () => {
    stubFetch({
      'GET /auth/session': () => jsonResponse({ detail: 'Authentication required' }, 401),
      'POST /auth/session/request': () =>
        jsonResponse({ status: 'code_requested', detail: '' }, 202),
    })
    renderWithProviders(<SignIn />)

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'manager@example.invalid' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send me a code' }))

    expect(await screen.findByLabelText('Sign-in code')).toBeInTheDocument()
  })

  it('never says whether the address was recognised', async () => {
    /**
     * **The property this test exists for is ADR-151 §2.**
     *
     * `POST /auth/session/request` answers 202 identically for a known address,
     * an unknown one, a deactivated account and a failed send, precisely so the
     * form cannot be used to discover who has an account. A UI that said "check
     * your inbox" for one and "no such account" for another would rebuild that
     * oracle in the interface, and the backend's uniform response would have
     * bought nothing.
     */
    stubFetch({
      'GET /auth/session': () => jsonResponse({ detail: 'Authentication required' }, 401),
      'POST /auth/session/request': () =>
        jsonResponse({ status: 'code_requested', detail: '' }, 202),
    })
    renderWithProviders(<SignIn />)

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'nobody@example.invalid' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send me a code' }))
    await screen.findByLabelText('Sign-in code')

    expect(screen.getByText(/if that address belongs to an active account/i)).toBeInTheDocument()
    expect(screen.queryByText(/no such account|not found|unknown address/i)).not.toBeInTheDocument()
  })

  it('leaves the sign-in screen once the code is accepted', async () => {
    /**
     * **The bug this test exists for, found by driving the real app.**
     *
     * Verifying returned 200, the cookie was set, the user was genuinely signed
     * in -- and the sign-in form just sat there. No error, no movement, nothing
     * to retry. Setting a cookie changes state; a route is not state, so
     * nothing moved. The two tests above both passed throughout, because they
     * asserted the steps and never the outcome.
     */
    let signedIn = false
    stubFetch({
      'GET /auth/session': () =>
        signedIn
          ? jsonResponse(A_SESSION)
          : jsonResponse({ detail: 'Authentication required' }, 401),
      'POST /auth/session/request': () =>
        jsonResponse({ status: 'code_requested', detail: '' }, 202),
      'POST /auth/session/verify': () => {
        signedIn = true
        return jsonResponse({ status: 'signed_in', user: A_SESSION.user, csrf_token: 't' })
      },
    })
    renderWithProviders(
      <Routes>
        <Route path="/sign-in" element={<SignIn />} />
        <Route path="/" element={<p>the shell</p>} />
      </Routes>,
      { route: '/sign-in' },
    )

    fireEvent.change(screen.getByLabelText('Email address'), {
      target: { value: 'manager@example.invalid' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Send me a code' }))
    fireEvent.change(await screen.findByLabelText('Sign-in code'), {
      target: { value: '424242' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('the shell')).toBeInTheDocument()
  })
})

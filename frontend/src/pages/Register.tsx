import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import { api } from '../libs/api.ts'
import {
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  normaliseEmail,
  registerValidationMessage,
} from '../libs/authValidation.ts'
import GradientButton from '../components/GradientButton'

function registerErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return 'Could not create account'
  }

  const status = error.response?.status
  const detail = error.response?.data?.detail

  // Duplicate email from POST /auth/register
  if (status === 400 && typeof detail === 'string') {
    return detail
  }

  // Pydantic validation (email format, password length)
  if (status === 422) {
    return 'Check your email and password (8-72 characters)'
  }

  return 'Could not create account'
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')

  async function handleRegister() {
    const validationError = registerValidationMessage(email, password, confirmPassword)
    if (validationError) {
      setError(validationError)
      return
    }

    try {
      await api.post('/auth/register', { email: normaliseEmail(email), password })
      // Drop a cached 401 from visiting a protected route while logged out
      queryClient.removeQueries({ queryKey: ['auth', 'me'] })
      navigate('/contacts')
    } catch (err) {
      setError(registerErrorMessage(err))
    }
  }

  return (
    <div className="relative flex min-h-dvh items-center justify-center overflow-hidden px-6">
      {/* Background image */}
      <img
        className="pointer-events-none absolute inset-0 h-full w-full object-cover"
        src="/backgrounds/wave-bg.svg"
        alt=""
        aria-hidden
      />

      <div className="relative w-full max-w-sm">
        {/* Logo */}
        <img
          className="mx-auto mb-8 h-14 w-14 object-contain"
          src="/brand/imet-logo.png"
          alt="iMet"
        />

        {/* Register form */}
        <form
          className="flex flex-col gap-4"
          noValidate
          onSubmit={e => {
            e.preventDefault()
            void handleRegister()
          }}
        >
          {/* Error message */}
          {error && <p className="text-error">{error}</p>}

          {/* Email input */}
          <label className="field">
            <span className="field-label">Email</span>
            <input
              type="email"
              className="input"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>

          {/* Password input */}
          <label className="field">
            <span className="field-label">Password</span>
            <input
              type="password"
              className="input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              minLength={PASSWORD_MIN_LENGTH}
              maxLength={PASSWORD_MAX_LENGTH}
              required
            />
          </label>

          {/* Confirm password input */}
          <label className="field">
            <span className="field-label">Confirm password</span>
            <input
              type="password"
              className="input"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              autoComplete="new-password"
              minLength={PASSWORD_MIN_LENGTH}
              maxLength={PASSWORD_MAX_LENGTH}
              required
            />
          </label>

          {/* Register button */}
          <div className="mt-2">
            <GradientButton type="submit">Create account</GradientButton>
          </div>
        </form>

        <p className="mt-4 text-center text-[14px] text-[var(--fg-2)]">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-[var(--violet)]">
            Log in
          </Link>
        </p>
      </div>
    </div>
  )
}

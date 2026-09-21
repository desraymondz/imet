import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { api } from '../libs/api.ts'
import { loginValidationMessage, normaliseEmail } from '../libs/authValidation.ts'
import GradientButton from '../components/GradientButton'

export default function LoginPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function handleLogin() {
    const validationError = loginValidationMessage(email, password)
    if (validationError) {
      setError(validationError)
      return
    }

    try {
      await api.post(
        '/auth/login',
        new URLSearchParams({ username: normaliseEmail(email), password }),
      )
      // Drop a cached 401 from visiting a protected route while logged out
      queryClient.removeQueries({ queryKey: ['auth', 'me'] })
      navigate('/contacts')
    } catch {
      setError('Invalid email or password')
    }
  }

  return (
    <div className="relative flex min-h-dvh flex-col overflow-hidden px-6">
      {/* Background image */}
      <img
        className="pointer-events-none absolute inset-0 h-full w-full object-cover"
        src="/backgrounds/wave-bg.svg"
        alt=""
        aria-hidden
      />

      <div className="relative flex flex-1 flex-col items-center justify-center">
        <div className="w-full max-w-sm">
          {/* Logo */}
          <img
            className="mx-auto mb-8 h-14 w-14 object-contain"
            src="/brand/imet-logo.png"
            alt="iMet"
          />

          {/* Login form */}
          <form
            className="flex flex-col gap-4"
            noValidate
            onSubmit={e => {
              e.preventDefault()
              void handleLogin()
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
                autoComplete="current-password"
                required
              />
            </label>

            {/* Login button */}
            <div className="mt-2">
              <GradientButton type="submit">Log in</GradientButton>
            </div>
          </form>
        </div>
      </div>

      <p className="relative pb-8 text-center text-[14px] text-[var(--fg-2)]">
        Don't have an account?{' '}
        <Link to="/register" className="font-medium text-[var(--violet)]">
          Create an account
        </Link>
      </p>
    </div>
  )
}
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../libs/api.ts'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function handleLogin(e: FormEvent) {
    e.preventDefault()
    try {
      const response = await api.post(
        '/auth/login',
        new URLSearchParams({ username: email, password }),
      )
      localStorage.setItem('token', response.data.access_token)
      navigate('/contacts')
    } catch {
      setError('Invalid email or password')
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

        {/* Login form */}
        <form className="flex flex-col gap-4" onSubmit={handleLogin}>
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
          <button type="submit" className="btn btn--primary btn--block mt-2">
            Log in
          </button>
        </form>
      </div>
    </div>
  )
}
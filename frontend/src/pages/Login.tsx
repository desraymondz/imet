import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../libs/api.ts'

export default function LoginPage() {
    const navigate = useNavigate()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')

    // Handle login form submission
    async function handleLogin(e: FormEvent) {
        e.preventDefault()
        try {
            // Login the user
            const response = await api.post(
                '/auth/login',
                new URLSearchParams({ username: email, password }),
            )
            // Set the JWT token in localStorage
            localStorage.setItem('token', response.data.access_token)
            // Redirect to the contacts page
            navigate('/contacts')
        } catch (error) {
            // Set the error message
            setError('Invalid email or password')
        }
    }

    return (
        <form onSubmit={handleLogin}>
            <h1>iMet</h1>
            {/* Display the error message */}
            {error && <p>{error}</p>}
            {/* Email input */}
            <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
            />
            {/* Password input */}
            <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
            />
            {/* Login button */}
            <button type="submit">Log in</button>
        </form>
    )
}

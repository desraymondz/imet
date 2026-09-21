// API client for the backend API

import axios from 'axios'

// Create a new axios instance with the base URL of the backend API
// withCredentials: send/store the HTTP-only session cookie
export const api = axios.create({
    baseURL: '/api',
    withCredentials: true,
})

// Redirect to login on 401 Unauthorised (expired/missing session)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // If the response is a 401 Unauthorized
        if (error.response?.status === 401) {
            const url = error.config?.url ?? ''
            // Login or register: 401 is a bad credential
            // /auth/me is handled by RequireAuth
            const skipRedirect =
                url.includes('/auth/login') ||
                url.includes('/auth/register') ||
                url.includes('/auth/me')
            if (!skipRedirect && window.location.pathname !== '/login') {
                window.location.href = '/login'
            }
        }
        return Promise.reject(error)
    }
)
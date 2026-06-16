// API client for the backend API

import axios from 'axios'

// Create a new axios instance with the base URL of the backend API
export const api = axios.create({
    baseURL: '/api',
})

// Attach JWT to every request automatically
// Reference: https://axios-http.com/docs/interceptors
api.interceptors.request.use((config) => {
    // Get the JWT token from localStorage
    // TODO: change to HTTP-only cookie
    const token = localStorage.getItem('token')
    
    // If the token is found, attach it to the request headers
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

// Redirect to login on 401 Unauthorized
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // If the response is a 401 Unauthorized
        if (error.response?.status === 401) {
            // Remove the JWT token from localStorage
            localStorage.removeItem('token')
            // Redirect to the login page by reloading the page
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)
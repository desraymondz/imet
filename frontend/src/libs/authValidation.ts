// Helper functions for shared login/register field checks

export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_LENGTH = 72

export function normaliseEmail(email: string): string {
  return email.trim().toLowerCase()
}

export function isValidEmail(email: string): boolean {
  const normalised = normaliseEmail(email)
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalised)
}

export function loginValidationMessage(email: string, password: string): string | null {
  if (!normaliseEmail(email)) {
    return 'Enter your email'
  }
  if (!isValidEmail(email)) {
    return 'Enter a valid email'
  }
  if (!password) {
    return 'Enter your password'
  }
  return null
}

export function registerValidationMessage(
  email: string,
  password: string,
  confirmPassword: string,
): string | null {
  if (!normaliseEmail(email)) {
    return 'Enter your email'
  }
  if (!isValidEmail(email)) {
    return 'Enter a valid email'
  }
  if (password.length < PASSWORD_MIN_LENGTH || password.length > PASSWORD_MAX_LENGTH) {
    return 'Password must be 8-72 characters'
  }
  if (password !== confirmPassword) {
    return 'Passwords do not match'
  }
  return null
}

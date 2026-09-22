// Helper functions for shared login/register field checks

export const PASSWORD_MIN_LENGTH = 8
export const PASSWORD_MAX_LENGTH = 72
// bcrypt hashes at most 72 bytes, and the API rejects anything longer
export const PASSWORD_MAX_BYTES = 72

function passwordByteLength(password: string): number {
  return new TextEncoder().encode(password).length
}

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
    return `Password must be ${PASSWORD_MIN_LENGTH}-${PASSWORD_MAX_LENGTH} alphanumeric characters`
  }
  if (passwordByteLength(password) > PASSWORD_MAX_BYTES) {
    // Accented characters and emoji take more than one byte
    return 'Password is too long. Accented characters and emoji count as more than one.'
  }
  if (password !== confirmPassword) {
    return 'Passwords do not match'
  }
  return null
}
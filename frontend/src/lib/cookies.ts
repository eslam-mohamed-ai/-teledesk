export function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop()?.split(";").shift() || null
  return null
}

export function setCookie(name: string, value: string, maxAgeSeconds: number) {
  if (typeof document === "undefined") return
  document.cookie = `${name}=${value}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax`
}

export function removeCookie(name: string, path = "/") {
  if (typeof document === "undefined") return
  document.cookie = `${name}=; Max-Age=0; Path=${path}; SameSite=Lax`
}

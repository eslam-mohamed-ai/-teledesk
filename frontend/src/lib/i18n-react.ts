import { useTranslation as useI18n } from "react-i18next"
import { Link as RouterLink } from "react-router-dom"

export function useTranslation() {
  const { t, i18n } = useI18n()
  return {
    t,
    i18n,
    changeLanguage: (lng: string) => i18n.changeLanguage(lng),
    language: i18n.language,
  }
}

export function Link({ to, children, className }: { to: string; children: React.ReactNode; className?: string }) {
  return <RouterLink to={to} className={className}>{children}</RouterLink>
}

export { useI18n }

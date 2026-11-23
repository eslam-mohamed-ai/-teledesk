import * as React from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { Shell } from "@/components/shell/layout"
import { ToastListener } from "@/components/ui/ToastListener"
import { useAuthStore } from "@/store/authStore"

// Pages (lazy loaded)
const Login = React.lazy(() => import("@/pages/auth/Login"))
const Signup = React.lazy(() => import("@/pages/auth/Signup"))
const ForgotPassword = React.lazy(() => import("@/pages/auth/ForgotPassword"))
const ResetPassword = React.lazy(() => import("@/pages/auth/ResetPassword"))
const VerifyEmail = React.lazy(() => import("@/pages/auth/VerifyEmail"))
const AcceptInvitation = React.lazy(() => import("@/pages/auth/AcceptInvitation"))
const Inbox = React.lazy(() => import("@/pages/inbox/Inbox"))
const Contacts = React.lazy(() => import("@/pages/contacts/Contacts"))
const Channels = React.lazy(() => import("@/pages/channels/Channels"))
const AI = React.lazy(() => import("@/pages/ai/AI"))
const Knowledge = React.lazy(() => import("@/pages/knowledge/Knowledge"))
const Analytics = React.lazy(() => import("@/pages/analytics/Analytics"))
const Settings = React.lazy(() => import("@/pages/settings/Settings"))
const Onboarding = React.lazy(() => import("@/pages/onboarding/Onboarding"))

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()
  if (isLoading) return <Splash />
  if (!isAuthenticated) return <Navigate to="/auth/login" replace />
  return <>{children}</>
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()
  if (isLoading) return <Splash />
  if (isAuthenticated) return <Navigate to="/inbox" replace />
  return <>{children}</>
}

function Splash() {
  return (
    <div className="flex h-screen w-full items-center justify-center bg-neutral-50">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
        <p className="text-sm text-neutral-500">Loading TeleDesk…</p>
      </div>
    </div>
  )
}

export function App() {
  const bootstrap = useAuthStore((s) => s.bootstrap)

  React.useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  return (
    <BrowserRouter>
      <ToastListener />
      <Routes>
        {/* Auth (guest) */}
        <Route path="/auth/login" element={<GuestRoute><Login /></GuestRoute>} />
        <Route path="/auth/signup" element={<GuestRoute><Signup /></GuestRoute>} />
        <Route path="/auth/forgot-password" element={<GuestRoute><ForgotPassword /></GuestRoute>} />
        <Route path="/auth/reset-password" element={<GuestRoute><ResetPassword /></GuestRoute>} />
        <Route path="/auth/verify-email" element={<GuestRoute><VerifyEmail /></GuestRoute>} />
        <Route path="/auth/accept-invitation" element={<GuestRoute><AcceptInvitation /></GuestRoute>} />

        {/* Protected */}
        <Route element={<ProtectedRoute><Shell /></ProtectedRoute>}>
          <Route path="/" element={<Navigate to="/inbox" replace />} />
          <Route path="/inbox" element={<Inbox />} />
          <Route path="/contacts" element={<Contacts />} />
          <Route path="/channels" element={<Channels />} />
          <Route path="/ai" element={<AI />} />
          <Route path="/knowledge" element={<Knowledge />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/onboarding" element={<Onboarding />} />
        </Route>

        <Route path="*" element={<Navigate to="/inbox" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
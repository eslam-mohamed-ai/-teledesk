import * as React from "react"
import { useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { useAuthStore } from "@/store/authStore"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Link, useTranslation } from "@/lib/i18n-react"

const schema = z.object({
  email: z.string().email("Invalid email"),
  password: z.string().min(1, "Password is required"),
})

export default function Login() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { setAuth, isLoading: storeLoading } = useAuthStore()
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  })

  const onSubmit = async (data: z.infer<typeof schema>) => {
    setError("")
    setIsLoading(true)
    try {
      const res = await api.post("/auth/login", data)
      const { user, email_verified } = res.data
      // Tokens are set in httpOnly cookies by the server
      setAuth(
        { id: user.id, name: user.name, email: user.email, role: user.role, email_verified },
        { id: user.id, name: user.name, plan: "free", onboarding_step: "profile", onboarding_completed_at: null, profile: {}, lead_capture_enabled: false, lead_capture_consent_text: "" },
      )
      if (!email_verified) {
        navigate("/auth/verify-email")
      } else {
        navigate("/inbox")
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || t("something_went_wrong"))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-screen w-full">
      <div className="hidden lg:w-1/2 bg-brand-600 flex items-center justify-center p-8">
        <div className="text-center text-white">
          <h1 className="text-4xl font-bold mb-4">TeleDesk</h1>
          <p className="text-brand-100">Omnichannel customer support inbox</p>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center bg-neutral-50 p-8">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{t("login")}</CardTitle>
            <CardDescription>Sign in to your account</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 p-3 rounded-md bg-red-50 text-red-600 text-sm">{error}</div>
            )}
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <Input label={t("email")} type="email" {...form.register("email")} />
              <Input label={t("password")} type="password" {...form.register("password")} />
              <div className="flex items-center justify-between">
                <Link to="/auth/forgot-password" className="text-sm text-brand-600 hover:underline">
                  {t("forgot_password")}
                </Link>
              </div>
              <Button type="submit" className="w-full" isLoading={isLoading}>
                {t("login")}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex flex-col gap-2">
            <p className="text-sm text-neutral-500 text-center">
              Don't have an account?{" "}
              <Link to="/auth/signup" className="text-brand-600 font-medium hover:underline">
                {t("signup")}
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

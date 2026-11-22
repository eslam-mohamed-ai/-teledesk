import * as React from "react"
import { useNavigate } from "react-router-dom"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Link, useTranslation } from "@/lib/i18n-react"

export default function VerifyEmail() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const verify = async () => {
    setIsLoading(true)
    try {
      // In a real flow, the token comes from URL params
      await api.post("/auth/verify-email", { token: "" })
      navigate("/inbox")
    } catch (e: any) {
      setError(e.response?.data?.detail || t("something_went_wrong"))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-neutral-50 p-8">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{t("verify_email")}</CardTitle>
          <CardDescription>Check your email to verify your account</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-50 text-red-600 text-sm">{error}</div>
          )}
          <p className="text-sm text-neutral-600 mb-6">
            A verification link has been sent to your email. Click the link to verify your account.
          </p>
          <Button onClick={verify} className="w-full" isLoading={isLoading}>
            I verified my email
          </Button>
        </CardContent>
        <CardFooter>
          <p className="text-sm text-neutral-500 text-center">
            Didn't receive the email?{" "}
            <Link to="/auth/resend-verification" className="text-brand-600 font-medium hover:underline">
              Resend
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}

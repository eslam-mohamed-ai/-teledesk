import * as React from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Link, useTranslation } from "@/lib/i18n-react"

const schema = z.object({
  email: z.string().email("Invalid email"),
})

export default function ForgotPassword() {
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = React.useState(false)
  const [message, setMessage] = React.useState("")
  const [error, setError] = React.useState("")

  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { email: "" },
  })

  const onSubmit = async (data: z.infer<typeof schema>) => {
    setError("")
    setMessage("")
    setIsLoading(true)
    try {
      await api.post("/auth/forgot-password", data)
      setMessage(t("reset_link_sent"))
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
          <CardTitle>{t("forgot_password")}</CardTitle>
          <CardDescription>Reset your password</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-50 text-red-600 text-sm">{error}</div>
          )}
          {message && (
            <div className="mb-4 p-3 rounded-md bg-green-50 text-green-600 text-sm">{message}</div>
          )}
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <Input label={t("email")} type="email" {...form.register("email")} />
            <Button type="submit" className="w-full" isLoading={isLoading}>
              {t("reset_password")}
            </Button>
          </form>
        </CardContent>
        <CardFooter>
          <p className="text-sm text-neutral-500 text-center">
            Remember your password?{" "}
            <Link to="/auth/login" className="text-brand-600 font-medium hover:underline">
              {t("login")}
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}

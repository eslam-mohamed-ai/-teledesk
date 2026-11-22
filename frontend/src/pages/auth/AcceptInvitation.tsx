import * as React from "react"
import { useSearchParams, useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Link, useTranslation } from "@/lib/i18n-react"

const schema = z.object({
  token: z.string().min(1, "Token is required"),
  name: z.string().min(1, "Name is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
})

export default function AcceptInvitation() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { token: searchParams.get("token") || "", name: "", password: "" },
  })

  const onSubmit = async (data: z.infer<typeof schema>) => {
    setError("")
    setIsLoading(true)
    try {
      const res = await api.post("/auth/accept-invitation", data)
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
          <CardTitle>{t("accept_invitation")}</CardTitle>
          <CardDescription>Create your account to join the team</CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="mb-4 p-3 rounded-md bg-red-50 text-red-600 text-sm">{error}</div>
          )}
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <Input label={t("name")} {...form.register("name")} />
            <Input label={t("password")} type="password" {...form.register("password")} />
            <Button type="submit" className="w-full" isLoading={isLoading}>
              {t("create_account")}
            </Button>
          </form>
        </CardContent>
        <CardFooter>
          <p className="text-sm text-neutral-500 text-center">
            Already have an account?{" "}
            <Link to="/auth/login" className="text-brand-600 font-medium hover:underline">
              {t("login")}
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}

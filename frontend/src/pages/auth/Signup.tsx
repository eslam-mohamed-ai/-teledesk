import * as React from "react"
import { useNavigate } from "react-router-dom"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Link, useTranslation } from "@/lib/i18n-react"

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Invalid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  lang: z.enum(["en", "ar"]),
})

export default function Signup() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = React.useState(false)
  const [error, setError] = React.useState("")

  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "", password: "", lang: "en" },
  })

  const onSubmit = async (data: z.infer<typeof schema>) => {
    setError("")
    setIsLoading(true)
    try {
      await api.post("/auth/register", data)
      navigate("/auth/verify-email", { state: { email: data.email } })
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
          <p className="text-brand-100">Start your omnichannel support inbox</p>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center bg-neutral-50 p-8">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>{t("signup")}</CardTitle>
            <CardDescription>Create your account</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 p-3 rounded-md bg-red-50 text-red-600 text-sm">{error}</div>
            )}
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <Input label={t("name")} {...form.register("name")} />
              <Input label={t("email")} type="email" {...form.register("email")} />
              <Input label={t("password")} type="password" {...form.register("password")} />
              <div className="flex items-center gap-2">
                <label className="text-sm text-neutral-600">{t("language")}</label>
                <select
                  {...form.register("lang")}
                  className="h-9 rounded-lg border border-neutral-300 bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-600"
                >
                  <option value="en">English</option>
                  <option value="ar">العربية</option>
                </select>
              </div>
              <Button type="submit" className="w-full" isLoading={isLoading}>
                {t("create_account")}
              </Button>
            </form>
          </CardContent>
          <CardFooter className="flex flex-col gap-2">
            <p className="text-sm text-neutral-500 text-center">
              Already have an account?{" "}
              <Link to="/auth/login" className="text-brand-600 font-medium hover:underline">
                {t("login")}
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

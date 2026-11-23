import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { FileText, Upload, Zap, Search, Trash2, Edit3 } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"
import { toast } from "@/components/ui/toaster"

type Document = {
  id: number
  name: string
  kind: string
  size: number
  status: string
  uses: number
  updated_at: string | null
}

export default function Knowledge() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: documents = [], isLoading } = useQuery<Document[]>({
    queryKey: ["documents"],
    queryFn: async () => {
      const res = await api.get("/documents")
      return res.data.items
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/documents/${id}`)
      return id
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      toast.success("Document deleted")
    },
    onError: (error) => {
      toast.error("Failed to delete document")
    },
  })

  const uploadRef = React.useRef<HTMLInputElement>(null)

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append("file", file)
    api.post("/documents/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }).then(() => {
      queryClient.invalidateQueries({ queryKey: ["documents"] })
      uploadRef.current!.value = ""
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">{t("knowledge_base")}</h1>
          <p className="text-neutral-500 dark:text-neutral-400">
            {t("upload_documents_to_train")}
          </p>
        </div>
        <Button onClick={() => uploadRef.current!.click()}>
          <Upload className="mr-2 h-4 w-4" /> {t("upload_document")}
        </Button>
        <input ref={uploadRef} type="file" className="hidden" onChange={handleUpload} />
      </div>

      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{t("documents")}</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-10">
                <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
              </div>
            ) : documents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <FileText className="h-12 w-12 text-neutral-400 mb-2" />
                <p className="text-sm text-neutral-500">{t("no_documents_yet")}</p>
              </div>
            ) : (
              <div className="space-y-3">
                {documents.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-3 bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-lg bg-neutral-100 flex items-center justify-center text-neutral-600">
                        <FileText className="h-4 w-4" />
                      </div>
                      <div className="flex flex-col min-w-0">
                        <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">{doc.name}</p>
                        <p className="text-xs text-neutral-500">
                          {Math.round(doc.size / 1024)} KB • {doc.uses} chunks
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={doc.status === "ready" ? "brand" : "secondary"} className="text-xs">
                        {doc.status}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => deleteMutation.mutate(doc.id)}
                        disabled={deleteMutation.isPending}
                        className="text-neutral-500 hover:text-red-600 hover:border-red-300 dark:hover:border-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
          <CardFooter className="flex justify-between items-center">
            <div className="flex justify-between text-sm mb-2 w-full">
              <span className="text-neutral-500">{t("documents_indexed")}</span>
              <span className="text-neutral-900 dark:text-neutral-100 font-medium">{documents.length}</span>
            </div>
            <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
              <div className="h-full bg-brand-600 rounded-full transition-all duration-500" style={{ width: "85%" }} />
            </div>
            <p className="text-xs text-neutral-500">{t("documents_processed_successfully")}</p>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}

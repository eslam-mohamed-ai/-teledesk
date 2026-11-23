import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Search, Mail, Phone, Tag, Users, Clock, Plus, MessageSquare } from "lucide-react"
import { useTranslation } from "@/lib/i18n-react"
import { cn } from "@/lib/utils"
import type { Contact } from "@/types/inbox"

type ContactNote = {
  id: number
  body: string
  created_at: string
  user_name: string | null
}

export default function Contacts() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [tab, setTab] = React.useState<string>("details")
  const [selectedContactId, setSelectedContactId] = React.useState<number | null>(null)
  const noteInputRef = React.useRef<HTMLInputElement>(null)

  const { data: contacts = [], isLoading } = useQuery<Contact[]>({
    queryKey: ["contacts"],
    queryFn: async () => {
      const res = await api.get("/contacts/")
      return res.data
    },
  })

  const notesQuery = useQuery<ContactNote[]>({
    queryKey: ["contact-notes", selectedContactId],
    queryFn: async () => {
      if (!selectedContactId) return []
      const res = await api.get(`/contacts/${selectedContactId}/notes`)
      return res.data
    },
    enabled: !!selectedContactId,
  })

  const addNoteMutation = useMutation({
    mutationFn: async ({ contactId, content }: { contactId: number; content: string }) => {
      const res = await api.post(`/contacts/${contactId}/notes`, { body: content })
      return res.data
    },
    onSuccess: (_, { contactId }) => {
      queryClient.invalidateQueries({ queryKey: ["contact-notes", contactId] })
      if (noteInputRef.current) noteInputRef.current.value = ""
    },
  })

  const handleAddNote = () => {
    if (!selectedContactId || !noteInputRef.current?.value?.trim()) return
    addNoteMutation.mutate({ contactId: selectedContactId, content: noteInputRef.current.value.trim() })
  }

  const getDisplayName = (contact: Contact) => contact.display_name || contact.first_name || contact.last_name || t("unknown_contact")

  return (
    <div className="flex h-full w-full">
      {/* Left: contacts list */}
      <div className="flex flex-col h-full border-r border-neutral-200 bg-white dark:border-neutral-700 dark:bg-neutral-900">
        <div className="h-12 border-b border-neutral-200 bg-white px-4 dark:border-neutral-700 dark:bg-neutral-900 flex items-center justify-between">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" />
            <input
              type="text"
              placeholder={t("search_contacts")}
              className="h-8 w-full pl-9 pr-3 rounded-lg border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-600 dark:bg-neutral-800 dark:border-neutral-700 dark:text-neutral-100 dark:focus:ring-brand-500"
            />
          </div>
          <Button size="sm">
            <Plus className="h-4 w-4 mr-2" /> {t("add_contact")}
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {isLoading ? (
            <div className="flex items-center justify-center py-10">
              <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
            </div>
          ) : contacts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-center px-4">
              <Users className="h-10 w-10 text-neutral-400 mb-2" />
              <p className="text-sm text-neutral-500">{t("no_contacts")}</p>
            </div>
          ) : (
            <div className="space-y-1">
              {contacts.map((contact) => (
                <button
                  key={contact.id}
                  onClick={() => setSelectedContactId(contact.id)}
                  className={cn(
                    "flex items-center justify-between gap-2 px-3 py-2 rounded-lg border text-left transition-colors",
                    selectedContactId === contact.id
                      ? "bg-brand-50 border-brand-200 dark:bg-brand-900/30 dark:border-brand-500"
                      : "bg-neutral-50 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-700",
                  )}
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <div className="h-8 w-8 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-600">
                      <Users className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col min-w-0">
                      <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100 truncate">
                        {getDisplayName(contact)}
                      </p>
                      <p className="text-xs text-neutral-500 truncate">{contact.email || contact.phone || t("no_contact_info")}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    {contact.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right: contact detail */}
      <div className="flex-1 flex flex-col h-full bg-neutral-50 dark:bg-neutral-950">
        {!selectedContactId ? (
          <div className="flex-1 flex items-center justify-center p-12 text-center">
            <div>
              <Users className="mx-auto mb-4 h-12 w-12 text-neutral-400" />
              <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">{t("select_contact")}</h3>
              <p className="text-neutral-500 dark:text-neutral-400 mt-1">
                {t("select_contact_prompt")}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col h-full">
            <div className="h-10 border-b border-neutral-200 bg-white px-4 dark:border-neutral-700 dark:bg-neutral-900 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-neutral-100 flex items-center justify-center text-neutral-600">
                  <Users className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                    {contacts.find((c) => c.id === selectedContactId)?.display_name || t("unknown_contact")}
                  </p>
                  <p className="text-xs text-neutral-500">{contacts.find((c) => c.id === selectedContactId)?.email || ""}</p>
                </div>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto">
              <Tabs defaultValue="details" onValueChange={(value) => setTab(value)}>
                <TabsList className="flex gap-1 p-4 mb-3">
                  <TabsTrigger value="details" className="px-4 py-2 text-sm font-medium transition-colors data-[state=active]:bg-brand-600 data-[state=active]:text-white rounded-lg">
                    {t("details")}
                  </TabsTrigger>
                  <TabsTrigger value="timeline" className="px-4 py-2 text-sm font-medium transition-colors data-[state=active]:bg-brand-600 data-[state=active]:text-white rounded-lg">
                    {t("timeline")}
                  </TabsTrigger>
                  <TabsTrigger value="notes" className="px-4 py-2 text-sm font-medium transition-colors data-[state=active]:bg-brand-600 data-[state=active]:text-white rounded-lg">
                    {t("notes")}
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="details" className="p-4 space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
                      <p className="text-xs text-neutral-500 uppercase font-medium mb-1">{t("email")}</p>
                      <p className="text-sm text-neutral-900 dark:text-neutral-100">{contacts.find((c) => c.id === selectedContactId)?.email || "—"}</p>
                    </div>
                    <div className="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
                      <p className="text-xs text-neutral-500 uppercase font-medium mb-1">{t("phone")}</p>
                      <p className="text-sm text-neutral-900 dark:text-neutral-100">{contacts.find((c) => c.id === selectedContactId)?.phone || "—"}</p>
                    </div>
                    <div className="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
                      <p className="text-xs text-neutral-500 uppercase font-medium mb-1">{t("language")}</p>
                      <p className="text-sm text-neutral-900 dark:text-neutral-100">{contacts.find((c) => c.id === selectedContactId)?.language || "—"}</p>
                    </div>
                    <div className="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
                      <p className="text-xs text-neutral-500 uppercase font-medium mb-1">{t("tags")}</p>
                      <div className="flex flex-wrap gap-1">
                        {contacts.find((c) => c.id === selectedContactId)?.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
                    <p className="text-xs text-neutral-500 uppercase font-medium mb-1">{t("ai_collected_fields")}</p>
                    <div className="flex flex-wrap gap-1">
                      {contacts.find((c) => c.id === selectedContactId)?.ai_collected_fields.map((field) => (
                        <Badge key={field} variant="brand" className="text-xs">
                          {field}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </TabsContent>
                <TabsContent value="timeline" className="p-4 space-y-4">
                  <div className="space-y-6">
                    <div className="flex items-start gap-3">
                      <div className="h-2 w-2 rounded-full bg-brand-500 mt-1" />
                      <div className="flex-1">
                        <p className="text-sm text-neutral-900 dark:text-neutral-100">{t("contact_created")}</p>
                      <p className="text-xs text-neutral-500">{contacts.find((c) => c.id === selectedContactId)?.created_at || t("just_now")}</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="h-2 w-2 rounded-full bg-neutral-400 mt-1" />
                      <div className="flex-1">
                        <p className="text-sm text-neutral-900 dark:text-neutral-100">{t("first_message_received")}</p>
                        <p className="text-xs text-neutral-500">{contacts.find((c) => c.id === selectedContactId)?.last_seen_at || t("just_now")}</p>
                      </div>
                    </div>
                  </div>
                </TabsContent>
                <TabsContent value="notes" className="p-4 space-y-4">
                  <div className="flex flex-col gap-3">
                    {notesQuery.data?.map((note) => (
                      <div key={note.id} className="bg-white dark:bg-neutral-800 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
                        <div className="flex justify-between items-start mb-2">
                          <p className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{note.user_name || t("you")}</p>
                          <p className="text-xs text-neutral-500">{note.created_at}</p>
                        </div>
                        <p className="text-sm text-neutral-700 dark:text-neutral-300">{note.body}</p>
                      </div>
                    ))}
                    <div className="flex gap-2">
                      <Input
                        placeholder={t("add_note")}
                        ref={(el) => { noteInputRef.current = el }}
                      />
                      <Button size="sm" onClick={handleAddNote} disabled={addNoteMutation.isPending || !noteInputRef.current?.value?.trim()}>
                        {t("add")}
                      </Button>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

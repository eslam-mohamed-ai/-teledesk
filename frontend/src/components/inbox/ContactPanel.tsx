import * as React from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  X,
  Mail,
  Phone,
  Globe,
  Clock,
  Tag as TagIcon,
  Plus,
  StickyNote,
  MessageSquare,
  Sparkles,
  User as UserIcon,
} from "lucide-react"
import { api, errorMessage } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { formatTime, initials, providerLabel, statusLabel } from "@/lib/format"
import type { Contact, Conversation } from "@/types/inbox"

type ContactNote = { id: number; body: string; created_at: string; user_name: string | null }
type ContactConversation = {
  id: number
  provider: string | null
  status: string
  last_preview: string | null
  created_at: string | null
  last_message_at: string | null
}

type Props = {
  conversation: Conversation
  onClose: () => void
}

const EDITABLE_FIELDS: { key: keyof Contact; label: string; icon: React.ElementType; type?: string }[] = [
  { key: "display_name", label: "Name", icon: UserIcon },
  { key: "email", label: "Email", icon: Mail, type: "email" },
  { key: "phone", label: "Phone", icon: Phone, type: "tel" },
  { key: "language", label: "Language", icon: Globe },
  { key: "country", label: "Country", icon: Globe },
  { key: "timezone", label: "Timezone", icon: Clock },
]

export function ContactPanel({ conversation, onClose }: Props) {
  const queryClient = useQueryClient()
  const contactId = conversation.contact_id
  const [tagInput, setTagInput] = React.useState("")
  const [noteInput, setNoteInput] = React.useState("")
  const [drafts, setDrafts] = React.useState<Record<string, string>>({})

  const contactQuery = useQuery<Contact>({
    queryKey: ["contact", contactId],
    queryFn: async () => (await api.get(`/contacts/${contactId}`)).data,
    enabled: !!contactId,
  })

  const notesQuery = useQuery<ContactNote[]>({
    queryKey: ["contact-notes", contactId],
    queryFn: async () => (await api.get(`/contacts/${contactId}/notes`)).data,
    enabled: !!contactId,
  })

  const conversationsQuery = useQuery<{ items: ContactConversation[] }>({
    queryKey: ["contact-conversations", contactId],
    queryFn: async () => (await api.get(`/contacts/${contactId}/conversations`)).data,
    enabled: !!contactId,
  })

  const contact = contactQuery.data
  const notes = Array.isArray(notesQuery.data) ? notesQuery.data : []

  React.useEffect(() => {
    if (!contact) return
    const next: Record<string, string> = {}
    for (const field of EDITABLE_FIELDS) {
      const value = contact[field.key]
      next[field.key as string] = value == null ? "" : String(value)
    }
    setDrafts(next)
  }, [contact])

  const updateMutation = useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) => {
      const res = await api.patch<Contact>(`/contacts/${contactId}`, { [key]: value || null })
      return res.data
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<Contact>(["contact", contactId], updated)
    },
  })

  const addTagMutation = useMutation({
    mutationFn: async (name: string) => {
      await api.post(`/contacts/${contactId}/tags`, { name })
      return name
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contact", contactId] })
      setTagInput("")
    },
  })

  const removeTagMutation = useMutation({
    mutationFn: async (name: string) => {
      await api.delete(`/contacts/${contactId}/tags/${encodeURIComponent(name)}`)
      return name
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contact", contactId] }),
  })

  const addNoteMutation = useMutation({
    mutationFn: async (body: string) => {
      const res = await api.post<ContactNote>(`/contacts/${contactId}/notes`, { body })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contact-notes", contactId] })
      setNoteInput("")
    },
  })

  if (!contactId) {
    return (
      <aside className="flex h-full w-80 shrink-0 flex-col border-l border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
        <div className="flex h-12 items-center justify-between border-b border-neutral-200 px-4 dark:border-neutral-800">
          <h3 className="text-sm font-semibold">Contact</h3>
          <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600" aria-label="Close contact panel">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <UserIcon className="mb-2 h-8 w-8 text-neutral-300" />
          <p className="text-sm text-neutral-500">No contact linked to this conversation.</p>
        </div>
      </aside>
    )
  }

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-l border-neutral-200 bg-white dark:border-neutral-800 dark:bg-neutral-900">
      <div className="flex h-12 items-center justify-between border-b border-neutral-200 px-4 dark:border-neutral-800">
        <h3 className="text-sm font-semibold text-neutral-800 dark:text-neutral-100">Contact details</h3>
        <button onClick={onClose} className="text-neutral-400 hover:text-neutral-600" aria-label="Close contact panel">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {contactQuery.isLoading ? (
          <div className="flex justify-center py-10">
            <div className="h-6 w-6 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
          </div>
        ) : contactQuery.isError ? (
          <div className="p-4 text-sm text-red-500">{errorMessage(contactQuery.error)}</div>
        ) : (
          <div className="divide-y divide-neutral-100 dark:divide-neutral-800">
            <div className="flex items-center gap-3 p-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">
                {initials(contact.display_name)}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-neutral-900 dark:text-neutral-100">
                  {contact.display_name || "Unknown contact"}
                </p>
                <p className="text-xs text-neutral-500">{contact.email || contact.phone || "No email or phone"}</p>
              </div>
            </div>

            <div className="space-y-2 p-4">
              {EDITABLE_FIELDS.map((field) => {
                const Icon = field.icon
                const key = field.key as string
                const value = drafts[key] ?? ""
                return (
                  <label key={key} className="flex items-center gap-2">
                    <Icon className="h-4 w-4 shrink-0 text-neutral-400" />
                    <input
                      type={field.type || "text"}
                      value={value}
                      placeholder={field.label}
                      onChange={(event) => setDrafts((prev) => ({ ...prev, [key]: event.target.value }))}
                      onBlur={() => {
                        if (value !== String(contact[field.key] ?? "")) {
                          updateMutation.mutate({ key, value })
                        }
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") event.currentTarget.blur()
                      }}
                      className="h-8 w-full rounded-md border border-transparent bg-neutral-50 px-2 text-xs text-neutral-800 outline-none focus:border-brand-500 focus:bg-white dark:bg-neutral-800 dark:text-neutral-100"
                    />
                  </label>
                )
              })}
            </div>

            <div className="p-4">
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <TagIcon className="h-3.5 w-3.5" /> Tags
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {(contact.tags ?? []).length === 0 && <span className="text-xs text-neutral-400">No tags</span>}
                {(contact.tags ?? []).map((tag) => (
                  <span
                    key={tag}
                    className="flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700"
                  >
                    {tag}
                    <button
                      onClick={() => removeTagMutation.mutate(tag)}
                      className="text-brand-500 hover:text-brand-800"
                      aria-label={`Remove ${tag}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
              <form
                className="mt-2 flex gap-1"
                onSubmit={(event) => {
                  event.preventDefault()
                  if (tagInput.trim()) addTagMutation.mutate(tagInput.trim())
                }}
              >
                <input
                  value={tagInput}
                  onChange={(event) => setTagInput(event.target.value)}
                  placeholder="Add tag"
                  className="h-8 flex-1 rounded-md border border-neutral-200 px-2 text-xs outline-none focus:border-brand-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
                />
                <Button size="sm" variant="outline" className="h-8 px-2" type="submit">
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </form>
            </div>

            {contact.ai_collected_fields?.length > 0 && (
              <div className="p-4">
                <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-violet-600">
                  <Sparkles className="h-3.5 w-3.5" /> AI-collected fields
                </h4>
                <div className="space-y-1.5">
                  {contact.ai_collected_fields.map((key) => (
                    <div
                      key={key}
                      className="rounded-lg border border-violet-200 bg-violet-50 px-2.5 py-1.5 text-xs dark:border-violet-900 dark:bg-violet-950/30"
                    >
                      <span className="font-semibold text-violet-700 dark:text-violet-300">{key}</span>
                      <span className="ml-2 text-violet-900 dark:text-violet-100">
                        {String(contact.custom_fields?.[key] ?? "")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="p-4">
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <StickyNote className="h-3.5 w-3.5" /> Notes
              </h4>
              <div className="space-y-2">
                {(notes).length === 0 && (
                  <p className="text-xs text-neutral-400">No notes yet.</p>
                )}
                {(notes).map((note) => (
                  <div key={note.id} className="rounded-lg bg-neutral-50 p-2 text-xs dark:bg-neutral-800">
                    <p className="whitespace-pre-wrap text-neutral-700 dark:text-neutral-200">{note.body}</p>
                    <p className="mt-1 text-[10px] text-neutral-400">
                      {note.user_name || "Agent"} · {formatTime(note.created_at)}
                    </p>
                  </div>
                ))}
              </div>
              <form
                className="mt-2 flex gap-1"
                onSubmit={(event) => {
                  event.preventDefault()
                  if (noteInput.trim()) addNoteMutation.mutate(noteInput.trim())
                }}
              >
                <input
                  value={noteInput}
                  onChange={(event) => setNoteInput(event.target.value)}
                  placeholder="Add a note"
                  className="h-8 flex-1 rounded-md border border-neutral-200 px-2 text-xs outline-none focus:border-brand-500 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-100"
                />
                <Button size="sm" variant="outline" className="h-8 px-2" type="submit">
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </form>
            </div>

            <div className="p-4">
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <MessageSquare className="h-3.5 w-3.5" /> Previous conversations
              </h4>
              <div className="space-y-1.5">
                {(conversationsQuery.data?.items ?? []).length === 0 && (
                  <p className="text-xs text-neutral-400">No previous conversations.</p>
                )}
                {(conversationsQuery.data?.items ?? []).map((item) => (
                  <div
                    key={item.id}
                    className={cn(
                      "rounded-lg border p-2 text-xs",
                      item.id === conversation.id
                        ? "border-brand-200 bg-brand-50 dark:border-brand-800 dark:bg-brand-950/30"
                        : "border-neutral-200 dark:border-neutral-700",
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-neutral-700 dark:text-neutral-200">
                        {providerLabel(item.provider)}
                      </span>
                      <span className="text-[10px] text-neutral-400">{statusLabel(item.status)}</span>
                    </div>
                    <p className="mt-0.5 truncate text-neutral-500 dark:text-neutral-400">
                      {item.last_preview || "No preview"}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
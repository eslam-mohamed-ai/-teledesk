export type Conversation = {
  id: number
  channel_id: number | null
  provider: string | null
  channel_provider: string | null
  contact_id: number | null
  contact_name: string | null
  assignee_user_id: number | null
  assignee_name: string | null
  status: string
  priority: string | null
  unread_count: number
  last_preview: string | null
  last_message_at: string | null
  last_inbound_at: string | null
  created_at: string | null
  ai_handling: boolean
  needs_human: boolean
  window_open: boolean
  window_expires_at: string | null
}

export type Message = {
  id: number
  role: string
  direction: string | null
  sender_type: string | null
  content: string | null
  content_type: string | null
  delivery_status: string | null
  error_code: string | null
  created_at: string | null
}

export type InternalNote = {
  id: number
  body: string
  at: string | null
}

export type ConversationPage = {
  items: Conversation[]
  has_more: boolean
  next_cursor: number | null
}

export type MessagePage = {
  items: Message[]
  has_more: boolean
  next_cursor: number | null
}

export type Contact = {
  id: number
  display_name: string | null
  first_name: string | null
  last_name: string | null
  email: string | null
  phone: string | null
  avatar_url: string | null
  language: string | null
  country: string | null
  timezone: string | null
  status: string | null
  custom_fields: Record<string, unknown> | null
  tags: string[]
  ai_collected_fields: string[]
  created_at: string
  last_seen_at: string | null
}

export type Member = {
  id: number
  name: string
  email: string
  role: string
  email_verified: boolean
  created_at: string
}

export type CannedReply = {
  id: number
  shortcut: string
  title: string
  body: string
}

export type Channel = {
  id: number
  provider: string
  external_id: string | null
  display_name: string | null
  status: string | null
  active: boolean
  capabilities: Record<string, unknown>
}

export type ProviderField = {
  key: string
  label: string
  type: string
  required: boolean
}

export type ProviderMetadata = {
  id: string
  label: string
  available: boolean
  coming_soon: boolean
  description: string
  fields: ProviderField[]
}
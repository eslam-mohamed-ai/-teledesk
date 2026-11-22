/**
 * Typed API client.
 *
 * Types in `./generated/schema.ts` are generated from the backend OpenAPI
 * schema (`npm run gen:api`). The helpers below add thin typed wrappers around
 * the axios instance so callers get request/response types from the schema.
 */

import type { components, paths } from "./generated/schema"
import { api } from "./api"
import type {
  Channel,
  Contact,
  Conversation,
  ConversationPage,
  InternalNote,
  Member,
  MessagePage,
  ProviderMetadata,
} from "@/types/inbox"

export type Schemas = components["schemas"]

type Method = "get" | "post" | "put" | "patch" | "delete"

type JsonBody<T> = T extends { content: { "application/json": infer R } } ? R : never

type Ok<P extends keyof paths, M extends Method> =
  paths[P][M] extends { responses: { 200: infer R } } ? JsonBody<R> : never

type Created<P extends keyof paths, M extends Method> =
  paths[P][M] extends { responses: { 201: infer R } } ? JsonBody<R> : never

type Result<P extends keyof paths, M extends Method> = [Ok<P, M>] extends [never]
  ? Created<P, M>
  : Ok<P, M>

type RequestBody<P extends keyof paths, M extends Method> =
  paths[P][M] extends {
    requestBody: { content: { "application/json": infer B } }
  }
    ? B
    : never

export const apiClient = {
  auth: {
    me: () => api.get<Schemas["UserOut"]>("/auth/me"),
    login: (body: Schemas["LoginIn"]) =>
      api.post<Result<"/api/auth/login", "post">>("/auth/login", body),
    register: (body: Schemas["RegisterIn"]) =>
      api.post<Result<"/api/auth/register", "post">>("/auth/register", body),
    refresh: () => api.post<Result<"/api/auth/refresh", "post">>("/auth/refresh", {}),
    logout: () => api.post<Result<"/api/auth/logout", "post">>("/auth/logout", {}),
  },

  company: {
    get: () => api.get<Result<"/api/company", "get">>("/company"),
    update: (body: RequestBody<"/api/company", "put">) =>
      api.put<Result<"/api/company", "put">>("/company", body),
  },

  channels: {
    list: () => api.get<{ items: Channel[] }>("/channels/"),
    providers: () => api.get<{ items: ProviderMetadata[] }>("/channels/providers"),
    connect: (provider: string, payload: Record<string, unknown>) =>
      api.post(`/channels/${provider}/connect`, { payload }),
    toggle: (id: number) => api.post(`/channels/${id}/toggle`),
    disconnect: (id: number) => api.post(`/channels/${id}/disconnect`),
    health: (id: number) => api.get<{ status: string }>(`/channels/${id}/health`),
  },

  conversations: {
    list: (params: Record<string, string | undefined> = {}) =>
      api.get<ConversationPage>("/conversations/", { params }),
    detail: (id: number) => api.get<Conversation>(`/conversations/${id}`),
    messages: (id: number, params: Record<string, string> = {}) =>
      api.get<MessagePage>(`/conversations/${id}/messages`, { params }),
    notes: (id: number) => api.get<{ items: InternalNote[] }>(`/conversations/${id}/notes`),
    reply: (id: number, text: string) => api.post(`/conversations/${id}/reply`, { text }),
    note: (id: number, note: string) => api.post(`/conversations/${id}/note`, { note }),
    assign: (id: number, assignee_user_id: number | null) =>
      api.post(`/conversations/${id}/assign`, { assignee_user_id }),
    take: (id: number) => api.post(`/conversations/${id}/take`),
    handBack: (id: number) => api.post(`/conversations/${id}/hand-back`),
    close: (id: number) => api.post(`/conversations/${id}/close`),
    reopen: (id: number) => api.post(`/conversations/${id}/reopen`),
    markRead: (id: number) => api.post(`/conversations/${id}/read`),
    retry: (id: number, messageId: number) =>
      api.post(`/conversations/${id}/messages/${messageId}/retry`),
  },

  contacts: {
    list: () => api.get<Contact[]>("/contacts/"),
    get: (id: number) => api.get<Contact>(`/contacts/${id}`),
    update: (id: number, body: Partial<Contact>) => api.patch<Contact>(`/contacts/${id}`, body),
    notes: (id: number) => api.get(`/contacts/${id}/notes`),
    addNote: (id: number, body: string) => api.post(`/contacts/${id}/notes`, { body }),
    conversations: (id: number) => api.get(`/contacts/${id}/conversations`),
    addTag: (id: number, name: string) => api.post(`/contacts/${id}/tags`, { name }),
    removeTag: (id: number, name: string) =>
      api.delete(`/contacts/${id}/tags/${encodeURIComponent(name)}`),
  },

  team: {
    members: () => api.get<Member[]>("/team/members"),
    invite: (email: string, role: string) => api.post("/team/invite", { email, role }),
  },

  onboarding: {
    state: () => api.get<Result<"/api/onboarding/state", "get">>("/onboarding/state"),
    checklist: () => api.get<Result<"/api/onboarding/checklist", "get">>("/onboarding/checklist"),
    saveStep: (step: string, data: Record<string, unknown>) =>
      api.post("/onboarding/step", { step, data }),
  },
}

export type ApiClient = typeof apiClient
# Facebook Messenger channel setup

Connect a Facebook Page to TeleDesk via the Messenger Platform so customers can
message your Page and receive AI-grounded replies.

## Prerequisites

- A Meta developer app with the **Messenger** product
- A Page access token (page-scoped) and the App secret (for webhook signature
  verification)
- A publicly reachable HTTPS webhook URL (`PUBLIC_BASE_URL`)

## Steps

1. **Create the app** — in [Meta for Developers](https://developers.facebook.com/),
   add the Messenger product and generate a Page access token.
2. **Subscribe the Page** — subscribe your app to the Page's `messages`,
   `messaging_postbacks`, and `messaging_optins` fields.
3. **Connect in TeleDesk** — `POST /api/channels/messenger/connect` with payload:
   ```json
   {
     "payload": {
       "access_token": "<PAGE_ACCESS_TOKEN>",
       "external_id": "<PAGE_ID>",
       "name": "My Page",
       "webhook_secret": "<APP_SECRET>"
     }
   }
   ```
   The adapter validates the token via the Graph API and derives `external_id`
   from the Page ID.
4. **Configure the Meta webhook** — callback URL:
   ```
   https://<PUBLIC_BASE_URL>/webhooks/messenger/<channel_id>
   ```
   Verify token = your `webhook_secret` (app secret). Meta sends
   `X-Hub-Signature-256`; TeleDesk verifies it via `verify_webhook_request`.

## Behavior

- Inbound messages create a contact + conversation automatically.
- The AI replies grounded on company documents.
- `/human` hands the conversation to a human agent (status `needs_human`).
- Meta's 24-hour messaging window applies; outbound outside the window may
  require a template message.

## Security

- The page access token is stored encrypted (`credentials_encrypted`) via the
  keyring; never returned or logged.
- Webhook signatures (`X-Hub-Signature-256`) are verified before enqueuing;
  invalid signatures return 403.
- Outbound Graph API calls go through `safe_fetch` (SSRF protection).

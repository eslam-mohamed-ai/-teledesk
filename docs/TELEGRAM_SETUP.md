# Telegram channel setup

Connect a Telegram bot to TeleDesk so customers can message your bot and receive
AI-grounded replies.

## Prerequisites

- A Telegram bot token from [@BotFather](https://t.me/botfather)
- A publicly reachable HTTPS URL for the webhook (use `ngrok` locally or your
  domain's `PUBLIC_BASE_URL` in production)

## Steps

1. **Create the bot** — message @BotFather, run `/newbot`, note the token.
2. **Set the webhook** — TeleDesk sets this automatically on connect, but you
   can verify:
   ```
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<PUBLIC_BASE_URL>/webhooks/telegram/<bot_id>"
   ```
3. **Connect in TeleDesk** — `POST /api/channels/telegram/connect` with payload:
   ```json
   {
     "payload": {
       "token": "<BOT_TOKEN>",
       "external_id": "<BOT_USERNAME>",
       "name": "My Telegram Bot",
       "webhook_secret": "<RANDOM_SECRET>"
     }
   }
   ```
   The adapter calls `getMe` to validate the token and derives `external_id`
   from the bot username.
4. **Set the Telegram secret token** — in @BotFather, use `/setdomain` or pass
   `X-Telegram-Bot-Api-Secret-Token` equal to your `webhook_secret` so the
   legacy `/webhooks/telegram/{bot_id}` route rejects forgery.

## Behavior

- Inbound messages create a contact + conversation automatically.
- The AI replies grounded on company documents.
- `/start` sends the company welcome message.
- `/human` hands the conversation to a human agent (status `needs_human`).
- Hourly limit: 20 customer messages per conversation.

## Security

- The bot token is stored encrypted (`credentials_encrypted`) via the keyring;
  never returned or logged.
- Webhook requests are verified via `verify_webhook_request` (Telegram secret
  token) before enqueuing.

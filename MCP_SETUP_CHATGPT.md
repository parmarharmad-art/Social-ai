# Connect SocialPilot AI to ChatGPT using MCP

SocialPilot AI exposes an authenticated **Streamable HTTP MCP** endpoint at:

`https://socialpilot-ai-mvp.onrender.com/mcp`

MCP tools included:
- Check automation configuration
- List Instagram content topic ideas
- Generate carousel copy, caption, CTA, hashtags and image prompt
- Generate and host an Instagram image
- View scheduled post queue
- Schedule a single Instagram image post
- Queue two AI-generated posts for a future date (10:00 and 18:00 India time)
- Fetch recent Instagram likes/comments report

## Security and billing

- The MCP endpoint requires an HTTP Bearer token. Set `MCP_ACCESS_TOKEN` as a private server environment variable. For a first setup, the server falls back to `AUTOMATION_API_KEY` if `MCP_ACCESS_TOKEN` is absent.
- Never put tokens in this repository or share them in a chat message.
- AI text/image generation uses the configured provider API and may incur charges.
- Scheduling tools create real post jobs. Publishing only works when the Instagram account, encrypted token storage, database, permissions and background scheduler are working.
- Keep automatic publishing and comment auto-replies disabled until end-to-end tests pass.

## ChatGPT connection

1. Deploy the latest repository revision so the live server includes the `/mcp` endpoint.
2. In the hosting service's environment settings, set a strong private `MCP_ACCESS_TOKEN`. If setting another secret is not possible, use the existing `AUTOMATION_API_KEY` as the bearer token.
3. In ChatGPT, open **Settings → Apps/Connectors** (the wording varies by account). If your account has developer/custom MCP connector support, add a remote MCP server using the URL above and **Bearer token** authentication. Paste the token into the connector's secure authentication field, not into a chat.
4. Start with `get_automation_status` and `list_scheduled_posts`. Try content generation only after the AI API key is configured. Do not enable live scheduling until the status and Instagram token storage are verified.

If ChatGPT does not show an option to add a custom MCP server, that feature may not be enabled for the current account/plan or client. The code can be deployed, but the ChatGPT-side connector must also be supported by the account.

## Local tests

Install dependencies with `pip install -r requirements.txt`, then start the service with `uvicorn app.server:app --host 0.0.0.0 --port 8000`.


## Instagram Agent Skills in ChatGPT

The MCP tool `run_instagram_agent_skill` runs one of these 13 workflows. Supply `skill_name` and a specific `brief`; include source text or metrics when the workflow depends on evidence.

| skill_name | Use |
| --- | --- |
| `ig-reel` | Reel hooks, script, time-coded beats, on-screen text and CTA |
| `ig-viral` | Analyze user-supplied public Reel examples; no claim of live browsing |
| `ig-caption` | Caption, opening preview, CTA and up to five hashtags |
| `ig-carousel` | Slide-by-slide copy and design guidance |
| `ig-story` | Story sequence and sticker suggestions |
| `ig-profile` | Audit supplied profile details and rewrite bio |
| `ig-plan` | Seven-day content plan |
| `ig-human` | Natural rewrite of supplied copy without inventing facts |
| `ig-comment` | Draft relevant comments for manual review |
| `ig-reply` | Classify supplied comments and draft replies |
| `ig-dm` | Consent-based DM copy drafts |
| `ig-repurpose` | Turn supplied long-form content into distinct posts |
| `ig-audit` | Analyze supplied post metrics and suggest experiments |

All outputs are drafts. The skill runner does not publish posts, post comments, or send DMs. It uses the configured OpenAI text model and may incur provider charges. The new code is not active on Render until the branch is merged and deployed.

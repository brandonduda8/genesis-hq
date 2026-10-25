# Genesis Alliance HQ

Development prototype for a phone-friendly Genesis command page and a GitHub mailbox message gateway.

Run tests using `npm run test:nexus`. Start locally using `npm start` with Node.js 20+.

Deployment target: Render free web service from `render.yaml`. Auto-deployment is disabled. Configure `NEXUS_OWNER_TOKEN` (unique random secret of at least 32 characters) and `NEXUS_GITHUB_TOKEN` (repository-scoped credential) using Render protected environment settings. Never commit credentials.

The dashboard can stage an objective to Claude or Zane and display metadata from GitHub mailbox routes. This does not guarantee agent receipt, model execution or 24-hour availability. An independent review and a live permissioned round-trip are required before activation. Render free services can sleep.

Operator engineering board: https://github.com/brandonduda8/astra-zane-bridge/issues/4

No paid capacity, automatic deployment or live host changes are part of this commit.

# Security policy

## Reporting a vulnerability

Please do not disclose credentials, tokens, or exploitable details in a public
issue. Use a private GitHub security advisory for this repository, or contact
the repository owner privately through GitHub.

## Deployment requirements

- Keep `.streamlit/secrets.toml` out of source control.
- Use the Supabase anon key for normal authenticated app operations.
- Keep `SUPABASE_SERVICE_ROLE_KEY` server-side and configure it only for the
  administrator registration dashboard.
- Apply both SQL migrations before enabling real users.
- Rotate any credential that appears in logs, screenshots, commits, or public
  messages.

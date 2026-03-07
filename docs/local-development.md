# Local Development Guide

This guide sets up a complete local development environment for the Sketchpad MCP server. After the one-time setup, running and testing the server is a two-command workflow.

## Prerequisites

- **Python 3.12** -- check with `python3 --version`
- **uv** -- install from [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
- **cloudflared** -- install with `brew install cloudflared` (macOS) or see [https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)
- **A Cloudflare account** with the `kempenich.dev` domain (for the named tunnel)
- **A GitHub OAuth App** -- see [github-oauth-app.md](github-oauth-app.md) if you haven't created one yet

## One-Time Setup

### 1. Install Dependencies

From the project root:

```bash
uv sync
```

**Verification:** `uv run python -c "import sketchpad"` completes without errors.

### 2. Create Your `.env` File

```bash
cp .env.example .env
```

### 3. Generate Secrets

Generate the JWT signing key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copy the output and set it as `JWT_SIGNING_KEY` in `.env`.

Generate the Fernet encryption key:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and set it as `STORAGE_ENCRYPTION_KEY` in `.env`.

**Verification:** Both values in `.env` should be long random strings, not the placeholder defaults.

### 4. Create a Named Cloudflare Tunnel

This gives you a **permanent URL** for local development, so you never have to update the GitHub OAuth callback URL after the initial setup.

The tunnel is called "TheMac" -- a general-purpose local dev tunnel (like "TheHome - K8s" is for the cluster). Sketchpad is one route; you can add more services later.

#### 4a. Log in to Cloudflare

```bash
cloudflared tunnel login
```

This opens a browser. Select the `kempenich.dev` domain and authorize. A certificate is saved to `~/.cloudflared/cert.pem`.

**Verification:** `ls ~/.cloudflared/cert.pem` shows the file.

#### 4b. Create the Tunnel

```bash
cloudflared tunnel create "TheMac"
```

This creates a tunnel and saves credentials to `~/.cloudflared/<TUNNEL_UUID>.json`.

Note the **Tunnel UUID** printed in the output -- you'll need it for the config file.

**Verification:** `cloudflared tunnel list` shows `TheMac` in the list alongside your other tunnels (DadHome, TheHome - HAOS, TheHome - K8s).

#### 4c. Add a DNS Route for Sketchpad

In the Cloudflare dashboard, go to the DNS settings for `kempenich.dev` and create a CNAME record:

| Field | Value |
|-------|-------|
| **Type** | `CNAME` |
| **Name** | `sketchpad` |
| **Target** | `<TUNNEL_UUID>.cfargotunnel.com` |
| **Proxy status** | Proxied (orange cloud) |

Replace `<TUNNEL_UUID>` with the UUID from step 4b. This points `sketchpad.kempenich.dev` to the TheMac tunnel.

You can add more routes later for other local services (e.g., `other-service.kempenich.dev`).

**Verification:** `dig sketchpad.kempenich.dev +short` returns Cloudflare proxy IPs (e.g., `104.21.x.x`, `172.67.x.x`). Cloudflare flattens the CNAME into A records, so you won't see a CNAME even though one was created.

#### 4d. Create the Tunnel Config

Create `~/.cloudflared/config-themac.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /Users/<you>/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: sketchpad.kempenich.dev
    service: http://localhost:8000
  # Add more local services here, e.g.:
  # - hostname: other-service.kempenich.dev
  #   service: http://localhost:3000
  - service: http_status:404
```

Replace `<TUNNEL_UUID>` with the UUID from step 4b and `<you>` with your username.

Then symlink it as the default config so `cloudflared tunnel run` works without `--config`:

```bash
ln -s ~/.cloudflared/config-themac.yml ~/.cloudflared/config.yml
```

Each tunnel gets its own named config file (e.g., `config-dadhome.yml`). The symlink points to whichever tunnel you use most often. To run a different tunnel, pass `--config` explicitly.

**Verification:** `cloudflared tunnel run` starts without errors (Ctrl-C to stop for now).

### 5. Update `.env` with the Tunnel URL

Set `SERVER_URL` in `.env` to your permanent tunnel URL:

```
SERVER_URL=https://sketchpad.kempenich.dev
```

### 6. Set the GitHub OAuth App Callback URL

Go to **[https://github.com/settings/developers](https://github.com/settings/developers)** > your OAuth App > edit.

Set the **Authorization callback URL** to:

```
https://sketchpad.kempenich.dev/auth/callback
```

This is a one-time step. The URL will never change because the named tunnel has a fixed hostname.

**Verification:** The callback URL on the GitHub OAuth App page shows `https://sketchpad.kempenich.dev/auth/callback`.

### 7. Set the GitHub Credentials in `.env`

Copy your GitHub OAuth App's **Client ID** and **Client Secret** into `.env`:

```
GITHUB_CLIENT_ID=Ov23li...
GITHUB_CLIENT_SECRET=abcdef1234...
```

**Verification:** Your `.env` now has all 4 required values set: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `JWT_SIGNING_KEY`, `STORAGE_ENCRYPTION_KEY`, and `SERVER_URL` points to the tunnel.

## Day-to-Day Workflow

After the one-time setup, running the server is two commands in two terminals.

### Terminal 1: Start the Tunnel

```bash
cloudflared tunnel run
```

Leave this running. You'll see connection logs as Cloudflare establishes the tunnel. (This uses `~/.cloudflared/config.yml`, which symlinks to `config-themac.yml`.)

### Terminal 2: Start the Server

```bash
uv run python -m sketchpad
```

The server starts on `http://localhost:8000` and reads all config from `.env`.

**Verification:** Visit `https://sketchpad.kempenich.dev/.well-known/oauth-authorization-server` in your browser. You should see the OAuth metadata JSON.

### Running the E2E Test

```bash
uv run python test_oauth.py
```

The script guides you through setup — it will prompt you to confirm the server and tunnel are running, verify connectivity to both, then run the full OAuth flow. The only manual step during the test is completing GitHub login in the browser.

## How It Works

```
Your Machine                      Cloudflare Edge              GitHub
------------                      ---------------              ------
MCP server (port 8000)  <----  sketchpad.              GitHub OAuth
       ^                       kempenich.dev           (callback URL set once)
       |                       (HTTPS termination)          |
cloudflared tunnel run              ^                       |
  (outbound connection)             |                       v
       |                       User's browser  --------> /auth/callback
       +------- http://localhost:8000                (via tunnel URL)
```

- `**SERVER_URL**` tells the MCP server its public identity. OAuth metadata, authorization URLs, and callback URLs all use this as the base.
- **cloudflared** creates an outbound-only encrypted tunnel -- no inbound ports needed.
- **The GitHub callback URL** (`/auth/callback`) is handled by FastMCP's `GitHubProvider`. It receives the GitHub authorization code, exchanges it for tokens, and redirects the user's browser to the client's `redirect_uri`.

## Troubleshooting

### Tunnel connected but server returns 502

cloudflared is running but the MCP server isn't. Start the server in Terminal 2.

### OAuth flow fails with "redirect_uri mismatch"

The GitHub OAuth App callback URL doesn't match what the server expects. The server expects `{SERVER_URL}/auth/callback`. Check:

1. `SERVER_URL` in `.env` matches your tunnel hostname exactly
2. The GitHub OAuth App callback URL is `{SERVER_URL}/auth/callback`

### "STORAGE_ENCRYPTION_KEY" / "JWT_SIGNING_KEY" errors at startup

These values are missing or malformed in `.env`. Regenerate them using the commands in step 3 above.
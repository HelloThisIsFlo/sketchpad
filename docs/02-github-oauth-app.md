# Creating the GitHub OAuth App

This guide walks through creating a GitHub OAuth App for the Sketchpad MCP server. The OAuth App provides the Client ID and Client Secret used by the server to authenticate users via GitHub.

## Prerequisites

- A GitHub account

## Steps

### 1. Open GitHub Developer Settings

Go to: **<https://github.com/settings/developers>**

You should see the "OAuth Apps" tab. If you have existing OAuth Apps, they'll be listed here.

### 2. Create a New OAuth App

Click **"New OAuth App"** (button in the top right).

### 3. Fill in the Application Details

| Field | Value |
|-------|-------|
| **Application name** | `Sketchpad` (or any name you prefer) |
| **Homepage URL** | `https://thehome-sketchpad.kempenich.dev` |
| **Application description** | (optional) MCP server for Claude AI integration |
| **Authorization callback URL** | `https://thehome-sketchpad.kempenich.dev/auth/callback` |

**Important:** The callback URL must match **exactly** what the FastMCP server expects. Phase 2 configures the server with this same URL. If they don't match, the OAuth flow will fail with a redirect_uri mismatch error.

### 4. Register the Application

Click **"Register application"**.

**Verification:** You should now see the application detail page with a **Client ID** displayed near the top.

### 5. Copy the Client ID

The **Client ID** is displayed on the application page. It looks like a 20-character hex string (e.g., `Ov23liAbCdEfGhIjKlMn`).

Copy it and save it somewhere safe -- you'll need it when creating the Kubernetes Secret.

### 6. Generate a Client Secret

Click **"Generate a new client secret"**.

### 7. Copy the Client Secret

The **Client Secret** is displayed **only once**. It looks like a 40-character hex string.

**Copy it immediately** and save it somewhere safe. If you lose it, you'll need to generate a new one.

**Verification:** You should see the Client Secret listed under "Client secrets" with a green dot indicating it's active. The secret value itself is only shown once -- after you navigate away, only the last 4 characters are visible.

### 8. Verify the OAuth App

After completing the steps above, verify:

- The app appears in your list at <https://github.com/settings/developers>
- The Client ID is visible on the app detail page
- One client secret is listed (you can see the last 4 characters)
- The callback URL shows `https://thehome-sketchpad.kempenich.dev/auth/callback`

## Creating the Kubernetes Secret

Once you have the Client ID and Client Secret, create the Kubernetes Secret:

```bash
kubectl create secret generic github-oauth \
  --namespace sketchpad \
  --from-literal=client-id='<YOUR_GITHUB_CLIENT_ID>' \
  --from-literal=client-secret='<YOUR_GITHUB_CLIENT_SECRET>'
```

Replace `<YOUR_GITHUB_CLIENT_ID>` and `<YOUR_GITHUB_CLIENT_SECRET>` with the actual values you copied.

See `k8s/secrets/README.md` for all secret creation commands.

## Notes

- The callback URL (`/auth/callback`) is where GitHub redirects users after they authorize the app. The FastMCP server handles this redirect in Phase 2.
- You can update the callback URL later if needed from the app settings page, but it must always match what the server expects.
- The OAuth App is not the same as a GitHub App. OAuth Apps are simpler and sufficient for this use case.

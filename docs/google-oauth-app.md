# Creating the Google OAuth App

This guide walks through creating a Google OAuth credential for the Sketchpad MCP server. The OAuth credential provides the Client ID and Client Secret used by the server to authenticate users via Google.

## Prerequisites

- A Google account
- Access to [Google Cloud Console](https://console.cloud.google.com/)

## Steps

### 1. Open Google Cloud Console

Go to: **<https://console.cloud.google.com/>**

If you don't have a Google Cloud project yet, you'll be prompted to create one. Any project name works (e.g., `sketchpad`).

### 2. Navigate to OAuth Consent Screen

Go to: **APIs & Services → OAuth consent screen**

Or direct link: **<https://console.cloud.google.com/apis/credentials/consent>**

### 3. Configure the Consent Screen

If this is your first time, you'll need to set up the consent screen:

| Field | Value |
|-------|-------|
| **App name** | `Sketchpad` (or any name you prefer) |
| **User support email** | Your email address |
| **Developer contact email** | Your email address |

Leave everything else as default and click **Save and Continue** through the remaining steps (Scopes, Test users, Summary).

**Note:** The app starts in "Testing" mode, which is fine — it means only your Google account can authorize. No need to publish or verify.

### 4. Create OAuth Credentials

Go to: **APIs & Services → Credentials**

Or direct link: **<https://console.cloud.google.com/apis/credentials>**

Click **"+ Create Credentials"** → **"OAuth client ID"**.

### 5. Fill in the Credential Details

| Field | Value |
|-------|-------|
| **Application type** | `Web application` |
| **Name** | `Sketchpad` (or any name you prefer) |
| **Authorized redirect URIs** | `https://themac-sketchpad.kempenich.dev/auth/callback` |

Leave **Authorized JavaScript origins** empty.

**Important:** The redirect URI must match **exactly** what the FastMCP server expects. The callback path `/auth/callback` is the same for all providers — only the env vars change.

### 6. Copy the Client ID and Client Secret

After clicking **"Create"**, a dialog appears showing both values:

- **Client ID** looks like: `123456789-abcdef.apps.googleusercontent.com`
- **Client Secret** looks like: `GOCSPX-AbCdEfGhIjKlMnOpQrStUvWxYz`

Copy both and save them somewhere safe.

**Verification:** The credential appears in your Credentials list with the name you chose.

### 7. Verify the OAuth Credential

After completing the steps above, verify:

- The credential appears in the Credentials page at <https://console.cloud.google.com/apis/credentials>
- Clicking the credential shows the correct Authorized redirect URI: `https://themac-sketchpad.kempenich.dev/auth/callback`
- The Client ID and Client Secret are saved somewhere accessible

## Using with Sketchpad

Set these values in your `.env`:

```bash
OAUTH_PROVIDER=google
GOOGLE_CLIENT_ID=123456789-abcdef.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-AbCdEfGhIjKlMnOpQrStUvWxYz
```

Then restart the server. The same callback URL works for both GitHub and Google — no Cloudflare or tunnel changes needed.

## Creating the Kubernetes Secret

Once you have the Client ID and Client Secret, create the Kubernetes Secret:

```bash
kubectl create secret generic google-oauth \
  --namespace sketchpad \
  --from-literal=client-id='<YOUR_GOOGLE_CLIENT_ID>' \
  --from-literal=client-secret='<YOUR_GOOGLE_CLIENT_SECRET>'
```

Replace the placeholder values with the actual credentials you copied.

## Notes

- The app stays in "Testing" mode — only your Google account can authorize. This is the right mode for a personal server.
- Google issues **refresh tokens** (unlike GitHub), so AUTH-05/AUTH-06 will be fully exercised with this provider.
- Google only issues a refresh token on the first consent. FastMCP defaults to `prompt=consent` which forces it every time, ensuring you always get one.
- If you ever need to reset, you can revoke access at <https://myaccount.google.com/permissions> and re-authorize.

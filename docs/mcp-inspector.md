# MCP Inspector Guide

MCP Inspector is an interactive debugging tool for MCP servers. It lets you browse tools, call them, and inspect the raw JSON-RPC messages -- useful for understanding how the protocol works before connecting Claude AI.

## Getting Started

Run the inspector (no install needed):

```bash
npx @anthropic/mcp-inspector
```

This opens a web UI (usually at `http://localhost:6274`).

## Connecting to Sketchpad

1. In the Inspector UI, set:
   - **Transport Type:** Streamable HTTP
   - **URL:** `http://localhost:8000/mcp` (or your tunnel URL)
2. Click **Connect**
3. The Inspector handles OAuth automatically -- it will open a browser window for GitHub login when needed

## Fun Things to Try

### 1. Browse the Tools

After connecting, go to the **Tools** tab. You should see two tools:

- **read_file** -- no arguments, returns the sketchpad contents
- **write_file** -- takes `content` (string) and optional `mode` ("replace" or "append")

Look at the tool descriptions -- they tell Claude AI what the tools are for and how to use them.

### 2. Read the Welcome Message

Call `read_file` with no arguments. If the sketchpad file does not exist yet, you will see the welcome message:

> Welcome to Sketchpad! Write something here.

### 3. Write Something

Call `write_file` with:
- `content`: `"# My First Note\n\nHello from MCP Inspector!"`

The response confirms the write and shows the file size.

### 4. Read It Back

Call `read_file` again. Your text should appear exactly as you wrote it.

### 5. Try Append Mode

Call `write_file` with:
- `content`: `"\n\n## Added Later\n\nThis was appended."`
- `mode`: `"append"`

Then `read_file` to see both sections together.

### 6. Check the OAuth Endpoints

Open a new browser tab and visit these URLs directly (replace the host if using a tunnel):

- `http://localhost:8000/.well-known/oauth-authorization-server` -- the OAuth server metadata (RFC 8414)
- `http://localhost:8000/.well-known/oauth-protected-resource` -- the protected resource metadata (RFC 9728)

These are the discovery endpoints that Claude AI uses to figure out how to authenticate.

### 7. Watch the Raw Messages

The Inspector shows the raw JSON-RPC messages in the **Messages** or **History** tab. Look for:
- `initialize` -- the handshake that starts every MCP session
- `tools/list` -- how the client discovers available tools
- `tools/call` -- the actual tool invocation with arguments and response

This is exactly what Claude AI sends and receives when using your server.

## Tips

- If you get a 401 error, the OAuth token may have expired. Reconnect and re-authenticate.
- The Inspector stores its OAuth tokens in the browser session. Clearing cookies will require re-authentication.
- If the server is behind a cloudflared tunnel, use the tunnel URL (e.g., `https://random-words.trycloudflare.com/mcp`) instead of localhost.

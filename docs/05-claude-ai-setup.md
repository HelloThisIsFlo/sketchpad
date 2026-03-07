# Setting Up Claude AI Integration

Connect Claude AI to the Sketchpad MCP server. Covers both the Claude Code CLI and phone (via claude.ai web connector).

## Claude Code CLI

Add the server and authenticate:

```bash
claude mcp add --transport http sketchpad https://sketchpad.kempenich.ai/mcp
```

Then inside Claude Code, run `/mcp` and select "Authenticate" for sketchpad. Complete the GitHub login in your browser. Once authenticated, Claude Code can call the sketchpad tools.

## Claude.ai (Phone)

Connectors added via claude.ai sync automatically to the Claude mobile apps.

1. Go to <https://claude.ai/settings/connectors>
2. Click "Add custom connector"
3. Enter URL: `https://sketchpad.kempenich.ai/mcp`
4. Give it a name (e.g., "Sketchpad")
5. Complete the OAuth flow in your browser (GitHub login)

The connector appears on your phone in Claude AI within a few minutes.

## Verify

Ask Claude to:

1. **Read** the sketchpad -- call `read_file`
2. **Write** something -- call `write_file` with test content
3. **Read back** -- call `read_file` again and confirm the content matches

All three should succeed. If you set up the Claude Code test skill (`.claude/skills/test-sketchpad/`), you can run `/test-sketchpad` for a guided walkthrough.

## Troubleshooting

### OAuth redirect mismatch

The GitHub OAuth App's callback URL must be `https://sketchpad.kempenich.ai/auth/callback`. Check the app settings at <https://github.com/settings/developers>. Note: the correct path is `/auth/callback`, not `/github/callback`.

### `about:blank` in browser during OAuth

Known bug ([#11814](https://github.com/anthropics/claude-code/issues/11814)). The claude.ai web OAuth flow may fail with an `about:blank` page. Use the Claude Code CLI instead -- it handles OAuth correctly.

### 502 or 503 errors

The server pod is not running. Check:

```bash
kubectl get pods -n sketchpad
kubectl logs -f deployment/sketchpad -n sketchpad
```

### "No tools available" in Claude

OAuth authentication was not completed. In Claude Code, run `/mcp` and authenticate for the sketchpad server. For claude.ai, re-add the connector at <https://claude.ai/settings/connectors>.

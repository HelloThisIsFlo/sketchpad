# Sketchpad Documentation

## Quick Start

For someone who has done this before -- all commands, no explanation:

```bash
# Build and deploy
make all

# Or step by step:
make build
make push
make deploy

# Verify
kubectl get pods -n sketchpad
curl -sf https://thehome-sketchpad.kempenich.dev/health

# Add to Claude Code
claude mcp add --transport http sketchpad https://thehome-sketchpad.kempenich.dev/mcp
# Then: /mcp -> Authenticate -> GitHub login
```

## Guides

Setup guides in order:

1. [Synology NFS Setup](01-synology-nfs.md) -- Configure NFS on Synology NAS for Kubernetes persistent storage
2. [GitHub OAuth App](02-github-oauth-app.md) -- Create the OAuth App for user authentication
3. [Cloudflare Tunnel](03-cloudflare-tunnel.md) -- Set up HTTPS ingress via Cloudflare Tunnel
4. [Deploy to Kubernetes](04-deploy.md) -- Build, push, and deploy the MCP server
5. [Claude AI Setup](05-claude-ai-setup.md) -- Connect Claude AI (CLI and phone)

## Supplementary

- [Google OAuth App](google-oauth-app.md) -- Alternative OAuth provider (Google instead of GitHub)
- [Local Development](local-development.md) -- Run the server locally for development
- [MCP Inspector](mcp-inspector.md) -- Debug MCP protocol with the interactive inspector tool

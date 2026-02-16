# Project Configuration

## n8n Integration Setup

This project is configured with n8n workflow automation capabilities through the n8n-mcp server and n8n-skills.

### Installation Status: ✅ COMPLETE

**Next Step:** Restart Claude Code to load the new skills and MCP server.

### What Was Installed

#### 1. Install n8n-skills (Claude Code Skills) ✅ COMPLETED

The following 7 skills have been installed to `~/.claude/skills/`:
- Expression syntax and patterns
- MCP tool usage for workflow building
- Workflow validation
- Node configuration best practices
- JavaScript/Python code node development
- 525+ n8n nodes support
- 2,653+ workflow templates for examples

The skills activate automatically when working with n8n-related tasks.

**Installed Skills:**
- `n8n-code-javascript` - JavaScript code node development patterns
- `n8n-code-python` - Python code node development patterns
- `n8n-expression-syntax` - n8n expression syntax and best practices
- `n8n-mcp-tools-expert` - Expert guidance on using MCP tools for workflows
- `n8n-node-configuration` - Node configuration best practices
- `n8n-validation-expert` - Workflow validation and quality checks
- `n8n-workflow-patterns` - Production-tested workflow patterns and templates

#### 2. Configure n8n-mcp Server (MCP Server) ✅ COMPLETED

The n8n-mcp server has been configured in `~/.claude/config.json`

**Current Configuration (Using npx):**

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true"
      }
    }
  }
}
```

**CRITICAL:** The `MCP_MODE: "stdio"` environment variable is required - omitting it causes JSON parsing errors.

**Option B: Using Hosted Service (Easiest)**

Access the cloud version at https://dashboard.n8n-mcp.com with free tier (100 tool calls/day).

**Option C: Docker Deployment**

```bash
docker pull ghcr.io/czlonkowski/n8n-mcp:latest
docker run -i --init ghcr.io/czlonkowski/n8n-mcp:latest
```

#### 3. Optional: Add n8n Instance Credentials

If you want to manage actual workflows (not just build them), add your n8n instance credentials to the MCP configuration:

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "N8N_API_URL": "http://your-n8n-instance:5678",
        "N8N_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

For local n8n instances, use `http://host.docker.internal:5678` with `WEBHOOK_SECURITY_MODE=moderate`.

### What This Enables

With both the MCP server and skills installed, Claude can:
- Access documentation for 1,084 n8n nodes (537 core + 547 community)
- Browse 2,709 workflow templates
- Build and validate n8n workflows
- Generate production-ready workflow configurations
- Provide real-world workflow examples
- Help with JavaScript/Python code nodes

### Safety Warning

⚠️ **NEVER edit production workflows directly with AI!** Always test changes in development environments first.

### Verification

After installation, verify setup by asking Claude:
- "List available n8n nodes for HTTP requests"
- "Show me a workflow template for Slack notifications"
- "Help me build a workflow that processes CSV files"

The n8n-skills should activate automatically, and the MCP server should provide comprehensive node documentation and templates.

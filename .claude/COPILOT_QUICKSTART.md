# Quick Start: Using GitHub Copilot with Claude Code

## TL;DR

Your DigniFi project now routes simple tasks to **free GitHub Copilot (GPT-4.1)** to save Claude tokens for complex bankruptcy logic.

## One-Time Setup (Do This Now)

### Authenticate with GitHub Copilot

✅ **Already completed!** You've authenticated with GitHub Copilot.

To test it works:

```bash
opencode run --model github-copilot/gpt-4.1 "Generate a hello world function"
```

That's it! The MCP server and subagent are already configured.

## How to Use

### Option 1: Let Claude Decide (Recommended)

Just work normally. Claude will automatically use the **copilot-delegate** subagent when appropriate.

```text
You: Create TypeScript interfaces for bankruptcy Form 101 fields

Claude: This is a simple boilerplate task, I'll delegate to Copilot...
[Uses copilot-delegate agent → saves your Claude tokens]
```

### Option 2: Explicit Delegation

Force a task to use Copilot:

```text
You: @copilot-delegate Generate Zod schema for income validation

[Copilot handles it directly via OpenCode]
```

## Three-Tier Optimization Strategy

### Tier 1: Free Models (GPT-4.1, Gemini)

- ✅ Form field TypeScript interfaces
- ✅ PDF mapping boilerplate
- ✅ Standard validators (SSN, ZIP, phone)
- ✅ CRUD scaffolding
- ✅ Test fixtures
- ✅ Code formatting

### Tier 2: Relaxed Limit Models (Claude Haiku/Sonnet via Copilot)

- 🔷 Creative content generation
- 🔷 Complex refactoring with reasoning
- 🔷 Multi-step logic (non-UPL)
- 🔷 Coordinated teamwork tasks
- 🔷 Form explainer content (non-legal)
- 🔷 Architecture decisions

### Tier 3: Premium (Claude Code - Main)

- 🎯 UPL boundary decisions
- 🎯 Means test eligibility logic
- 🎯 Trauma-informed content
- 🎯 District-specific rules
- 🎯 Credit counseling integration
- 🎯 Legal deadline calculations

## Token Savings

Expected savings during MVP development:

- **90% reduction** on boilerplate code generation
- **60% overall** token usage reduction
- **More capacity** for complex legal logic

## Verify It's Working

```bash
# Check Copilot authentication
opencode --model github/copilot "test"

# Check MCP server config
cat .claude/mcp.json

# Check agent exists
ls -la ~/.claude/agents/copilot-delegate.md
```

## Troubleshooting

### Copilot not authenticated

```bash
opencode run --model github-copilot/gpt-4.1 "test"
# If it fails, re-authenticate with: opencode auth
```

### MCP server not found

```bash
# Check opencode-acp is installed
which opencode-acp

# Restart Claude Code to reload MCP config
```

## Full Documentation

See `.claude/COPILOT_INTEGRATION.md` for:
- Detailed architecture
- Task routing rules
- Audit logging requirements
- Legal compliance notes
- Usage examples

---

**Ready to use.** Just start working on DigniFi features and Claude will optimize token usage automatically.

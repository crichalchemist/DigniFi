# GitHub Copilot + OpenCode Integration for DigniFi

## Overview

This document explains how DigniFi uses GitHub Copilot via OpenCode and the opencode-acp adapter to optimize token usage and preserve Claude's rate limits for complex bankruptcy logic.

## Architecture

```
User Request
    ↓
Claude Code (Orchestrator)
    ↓
Decision: Simple or Complex?
    ├─→ Simple Task → copilot-delegate subagent → OpenCode MCP → GitHub Copilot (FREE GPT-4.1)
    └─→ Complex Task → Claude (Premium tokens for UPL logic, trauma-informed content)
```

## Setup Complete ✓

The following components are now configured:

1. **✓ OpenCode CLI** - Verify installation location:

   ```bash
   which opencode
   # Typical output: /usr/local/bin/opencode or /Users/username/.opencode/bin/opencode
   ```

2. **✓ opencode-acp adapter** - Verify adapter location:

   ```bash
   which opencode-acp
   # Typical output: /opt/local/bin/opencode-acp or /Users/username/.local/bin/opencode-acp
   ```

3. **✓ MCP Server Config** - Update `.claude/mcp.json` with your specific paths:

   ```json
   "env": {
     "OPENCODE_BIN": "/verified/path/to/opencode",
     "ADAPTER_PATH": "/verified/path/to/opencode-acp"
   }
   ```
4. **✓ Copilot Delegate Agent** - `{USER_HOME}/.claude/agents/copilot-delegate.md`

## GitHub Copilot Authentication

### First-Time Setup

1. **Start OpenCode and select GitHub Copilot:**
   ```bash
   opencode
   # Select "GitHub Copilot" from the model list
   # Or run: opencode --model github/copilot
   ```

2. **Authenticate with GitHub:**
   ```bash
   # OpenCode will prompt you to visit:
   # https://github.com/login/device

   # Enter the device code displayed in the terminal
   # Grant permission to access GitHub Copilot
   ```

3. **Verify authentication:**
   ```bash
   opencode "test prompt"
   # Should return a response from GitHub Copilot
   ```

### Checking Current Status

```bash
# Check if Copilot is authenticated
opencode --model github/copilot "echo test"
```

## Task Routing Rules for DigniFi

### Delegate to GitHub Copilot (Simple Tasks)

Use the **copilot-delegate** agent for:

- **Form field interfaces** - TypeScript types for Forms 101-128
  ```typescript
  // Example: Generate Form 101 interface
  interface Form101 {
    debtorName: string;
    address: Address;
    ssn: string;
    caseNumber?: string;
  }
  ```

- **PDF field mapping** - Boilerplate for populating fillable PDFs
  ```python
  # Example: PDF field mapping utilities
  FORM_101_FIELDS = {
      "debtor_name_first": "Text1",
      "debtor_name_last": "Text2",
      # ...
  }
  ```

- **Standard validators** - SSN, ZIP, phone number validation
  ```python
  def validate_ssn(ssn: str) -> bool:
      return re.match(r'^\d{3}-\d{2}-\d{4}$', ssn) is not None
  ```

- **CRUD operations** - Basic database queries and models
- **Test fixtures** - Sample bankruptcy data for testing
- **Code formatting** - Style cleanup and refactoring

### Keep in Claude (Complex Tasks)

**DO NOT delegate** these to Copilot:

- **UPL boundary decisions** - Any legal advice vs. information distinction
- **Means test calculations** - 11 U.S.C. § 707(b) eligibility logic
- **District-specific rules** - 94 federal districts have varying local rules
- **Trauma-informed content** - Plain-language explanations requiring empathy
- **Credit counseling integration** - DOJ-approved provider verification
- **Deadline calculations** - 341 meeting scheduling, plan confirmation dates
- **Fee waiver logic** - 28 U.S.C. § 1930(f) qualification

## Usage Examples

### Example 1: Generate Form Field Interface

**User request:** "Create a TypeScript interface for bankruptcy Form 122A-1 (Chapter 7 Means Test)"

**Claude's decision:**
- Simple task → Delegate to copilot-delegate agent
- No UPL sensitivity in interface structure

```bash
# Copilot-delegate agent invokes:
opencode "Generate TypeScript interface for bankruptcy Form 122A-1 with fields: marital_status, dependents, income_last_6_months (array of monthly amounts), deductions"
```

### Example 2: UPL-Sensitive Guidance Content

**User request:** "Write plain-language explanation of when someone should file Chapter 7 vs. Chapter 13"

**Claude's decision:**
- Complex task → Claude handles directly
- UPL-sensitive (legal advice vs. information boundary)
- Requires trauma-informed tone

Claude generates content with careful disclaimers and information-only framing.

### Example 3: PDF Field Mapping Boilerplate

**User request:** "Create a Python function to map our intake data to Form 101 PDF fields"

**Claude's decision:**
- Simple task → Delegate to copilot-delegate agent
- Standard boilerplate code

```bash
# Copilot-delegate agent invokes:
opencode "Create Python function that takes a dictionary of user intake data and maps it to Form 101 PDF field names using pdfrw library"
```

## Invoking the Copilot Delegate Agent

### Manual Invocation

When you want to explicitly use Copilot for a simple task:

```
You: @copilot-delegate Generate a Zod schema for validating bankruptcy means test income fields
```

### Automatic Routing

Claude Code should automatically consider task difficulty and route them to the copilot-delegate agent based on task complexity analysis.

## Token Usage Optimization

### Token Cost Comparison

| Task Type | Without Copilot | With Copilot | Savings |
|-----------|----------------|--------------|---------|
| Form interface (100 fields) | ~2,000 tokens | ~200 tokens | 90% |
| PDF field mapping (500 LOC) | ~8,000 tokens | ~800 tokens | 90% |
| Standard validators (10 functions) | ~1,500 tokens | ~150 tokens | 90% |
| **Complex UPL decision** | ~3,000 tokens | ~3,000 tokens | 0% (kept in Claude) |
| **Trauma-informed content** | ~2,500 tokens | ~2,500 tokens | 0% (kept in Claude) |

### Estimated Monthly Savings

Assuming DigniFi development phase (MVP):

- **Simple tasks:** ~50,000 tokens/day → 45,000 saved (90% to Copilot)
- **Complex tasks:** ~25,000 tokens/day → 0 saved (stays in Claude)
- **Total savings:** ~1.35M tokens/month (60% reduction)
- **Rate limit impact:** 60% more capacity for complex legal logic

## Configuration Files

### `.claude/mcp.json`

Configures the OpenCode-Copilot MCP server:

```json
{
  "mcpServers": {
    "opencode-copilot": {
      "command": "opencode-acp",
      "env": {
        "OPENCODE_CONFIG_CONTENT": "{\"model\":\"github/copilot\"}",
        "OPENCODE_BIN": "$HOME/.opencode/bin/opencode"
      }
    }
  }
}
```

### `~/.claude/agents/copilot-delegate.md`

Defines the subagent that delegates to Copilot with task routing rules.

## Monitoring and Debugging

### Check MCP Server Status

```bash
# Verify opencode-acp is running
ps aux | grep opencode-acp

# Test OpenCode directly
opencode --model github/copilot "test prompt"
```

### View Delegation Logs

Claude Code logs subagent invocations. Check:

```bash
# Claude Code session logs
tail -f ~/.claude/history.jsonl | grep copilot-delegate
```

### Debugging Issues

**Issue: Copilot not authenticated**

```bash
# Re-authenticate
opencode --model github/copilot
# Follow device code flow at https://github.com/login/device
```

**Issue: MCP server not starting**

```bash
# Check opencode-acp binary
which opencode-acp
opencode-acp --version

# Verify Node.js is installed (required for opencode-acp)
node --version  # Should be 18+
```

**Issue: Task not being delegated**

- Check if task matches routing rules in `copilot-delegate.md`
- Explicitly invoke: `@copilot-delegate <task>`

## Legal Compliance Notes

### Audit Logging

All delegated tasks should be logged for legal compliance review:

```python
# Example audit log entry
{
    "timestamp": "2026-01-03T10:30:00Z",
    "agent": "copilot-delegate",
    "task": "Generate Form 101 interface",
    "model": "github/copilot",
    "output_hash": "abc123...",
    "reviewed": false
}
```

### Review Requirements

**CRITICAL:** Even though Copilot handles "simple" tasks, DigniFi's legal compliance requires:

1. **Code review** - All generated code must be reviewed by developers
2. **Legal review** - Any user-facing text (even generic disclaimers) must be reviewed by counsel
3. **Audit trail** - Maintain logs of what tasks were delegated and when
4. **Validation testing** - Generated validation logic must pass test suites

### UPL Safeguards

The routing rules ensure UPL-sensitive tasks **never** go to Copilot:

- Legal advice/information interpretation as written, boundary decisions → Claude only
- Eligibility recommendations → Claude only
- District-specific legal interpretations → Claude only
- User-facing guidance content → Claude only (with subsequent legal review)

## Future Enhancements

### Planned Improvements

1. **Automatic task classification** - ML model to classify tasks as simple/complex
2. **Confidence scoring** - Route to Claude if Copilot confidence < 90%
3. **Multi-model routing** - Use different free models for different task types
4. **Cost tracking** - Monitor token savings in real-time dashboard
5. **Quality metrics** - Track Copilot output quality and escalation rate

### Alternative Models

Beyond GitHub Copilot, consider integrating:

- **Google Gemini** (free tier for simple tasks)
- **Local models** (Llama, CodeLlama for air-gapped compliance)
- **Specialized legal models** (if UPL-compliant options emerge)

## Support and Troubleshooting

### Resources

- **OpenCode Documentation:** [OpenCode Documentation](https://opencode.ai/docs/)
- **opencode-acp GitHub:** [opencode-acp GitHub](https://github.com/josephschmitt/opencode-acp)
- **GitHub Copilot Models:** [GitHub Copilot Models](https://docs.github.com/en/copilot/reference/ai-models/supported-models)
- **Claude Code MCP Docs:** [Claude Code MCP Docs](https://code.claude.com/docs/en/mcp.md)

### Getting Help

For issues specific to DigniFi integration:
1. Check this document first
2. Review `.claude/mcp.json` and agent configuration
3. Test OpenCode directly to isolate issues
4. Check Claude Code history logs for delegation patterns

---

**Status:** Active Integration ✅
**Last Updated:** 2026-01-03
**Next Review:** 2026-02-01 (monthly review of routing rules and token savings)
# .mimocode/hooks/

Project-level hooks for the `.remember/` continuity system.

| Hook                | Trigger                 | Purpose                                                                        |
| ------------------- | ----------------------- | ------------------------------------------------------------------------------ |
| `session-start.sh`  | Session start           | Inject `now.md`, today's log, recent, archive into context; run daily rollover |
| `post-save.sh`      | After significant work  | Append timestamped entry to `today-YYYY-MM-DD.md`                              |
| `daily-rollover.sh` | Session start or manual | Rename yesterday's `.md` → `.done.md`, update archive + recent                 |

## Usage

```bash
# Inject state at session start
.mimocode/hooks/session-start.sh

# Log completed work
.mimocode/hooks/post-save.sh "feature/form-fill-engine" "Migrated Form 107 to FillResolver"

# Manual rollover
.mimocode/hooks/daily-rollover.sh
```

## How they connect to the existing plugin

These hooks extend the official `remember` plugin (v0.7.3). The plugin handles:

- Auto-save via `post-tool-hook.sh` (session JSONL → markdown)
- Recovery via `session-start-hook.sh`
- Consolidation via `run-consolidation.sh`

These project hooks add:

- Clean daily rollover (the plugin's consolidation requires Python pipeline + Haiku)
- Simple append-only logging without LLM calls
- Cross-harness portability (plain bash, no plugin deps)

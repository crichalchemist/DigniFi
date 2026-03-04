# Global Pre-Commit Setup

This guide shows how to configure pre-commit hooks globally across all your git repositories.

## Option 1: Git Init Template (Automatic for All New Repos)

### Setup

```bash
# 1. Create git template directory
mkdir -p ~/.git-templates/hooks

# 2. Configure git to use this template
git config --global init.templateDir ~/.git-templates

# 3. Create pre-commit hook script
cat > ~/.git-templates/hooks/pre-commit << 'EOF'
#!/bin/bash
# Auto-install pre-commit hooks if .pre-commit-config.yaml exists

if [ -f ".pre-commit-config.yaml" ]; then
    if ! command -v pre-commit &> /dev/null; then
        echo "⚠️  pre-commit not installed. Install with: pip install pre-commit"
        exit 0
    fi

    if [ ! -f ".git/hooks/pre-commit" ] || ! grep -q "pre-commit" ".git/hooks/pre-commit"; then
        echo "📦 Installing pre-commit hooks..."
        pre-commit install
    fi

    # Run pre-commit
    pre-commit run --config .pre-commit-config.yaml
else
    # No pre-commit config, allow commit
    exit 0
fi
EOF

# 4. Make it executable
chmod +x ~/.git-templates/hooks/pre-commit

# 5. Apply to existing repos
cd /path/to/repo
git init  # Re-initializes using template (safe, doesn't delete anything)
```

### How It Works

- All new `git init` or `git clone` repos automatically get the hook
- Hook checks for `.pre-commit-config.yaml` in the repo
- If found, runs pre-commit automatically
- If not found, allows commit (backward compatible)

## Option 2: Global Pre-Commit Config (Same Rules Everywhere)

### Setup

```bash
# 1. Create global pre-commit config
cat > ~/.pre-commit-config.yaml << 'EOF'
# Global pre-commit hooks for all repositories
repos:
  # Basic file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ['--maxkb=500']

  # Secrets detection
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
EOF

# 2. Install pre-commit globally
pip install --user pre-commit

# 3. For each repo, run:
cd /path/to/repo
pre-commit install --config ~/.pre-commit-config.yaml
```

### How It Works

- All repos use the same global config
- Good for basic checks (whitespace, secrets, merge conflicts)
- Doesn't override project-specific configs

## Option 3: Shell Alias (Run Before Commit)

### Setup

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Pre-commit aliases
alias gc='pre-commit run && git commit'
alias gca='pre-commit run && git commit -a'
alias gcm='pre-commit run && git commit -m'

# Or wrap git commit entirely
git() {
    if [[ "$1" == "commit" ]] && [ -f ".pre-commit-config.yaml" ]; then
        pre-commit run --all-files || return 1
    fi
    command git "$@"
}
```

### How It Works

- Wraps `git commit` command
- Runs pre-commit before commit
- Works with existing workflow

## Option 4: Global Git Hooks Manager (Husky Alternative)

### Setup

```bash
# Install global git hooks manager
npm install -g simple-git-hooks

# Create ~/.simple-git-hooks.json
cat > ~/.simple-git-hooks.json << 'EOF'
{
  "pre-commit": "pre-commit run --all-files"
}
EOF

# For each repo:
cd /path/to/repo
simple-git-hooks install
```

## Recommended Approach

**For personal projects:**

- Use Option 1 (Git Init Template) for automatic hook installation
- Override with project-specific `.pre-commit-config.yaml` as needed

**For team projects:**

- Use project-specific `.pre-commit-config.yaml` (like DigniFi)
- Document in README for team members to install

**For maximum security:**

- Use Option 2 with secrets detection globally
- Layer with project-specific linting

## Example: Combined Approach

```bash
# ~/.git-templates/hooks/pre-commit
#!/bin/bash

# 1. Check for local pre-commit config
if [ -f ".pre-commit-config.yaml" ]; then
    pre-commit run --config .pre-commit-config.yaml
    exit $?
fi

# 2. Fall back to global config
if [ -f "$HOME/.pre-commit-config.yaml" ]; then
    pre-commit run --config "$HOME/.pre-commit-config.yaml"
    exit $?
fi

# 3. Run basic checks manually
echo "⚠️  No pre-commit config found. Running basic checks..."
git diff --cached --name-only | xargs grep -l 'password\|secret\|api[_-]key' && {
    echo "❌ Potential secrets detected in commit!"
    exit 1
}

exit 0
```

## Applying to Existing Repos

```bash
# Update all repos in a directory
for repo in ~/projects/*; do
    if [ -d "$repo/.git" ]; then
        cd "$repo"
        git init  # Re-initialize with template
        echo "✅ Updated $repo"
    fi
done
```

## IDE Integration

### VS Code

Install extensions:

- `ms-python.black-formatter` - Black formatting
- `dbaeumer.vscode-eslint` - ESLint
- `esbenp.prettier-vscode` - Prettier

Enable format on save in `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "[javascript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### PyCharm / IntelliJ

1. Settings → Tools → External Tools
2. Add "Black" and "Ruff" tools
3. Settings → Tools → File Watchers → Add file watcher for auto-format

## Troubleshooting

### Hook Not Running

```bash
# Check if hook is installed
ls -la .git/hooks/pre-commit

# Reinstall
pre-commit install --force
```

### Slow Commits

Pre-commit caches environments. First run is slow, subsequent runs are fast.

```bash
# Pre-install all hooks
pre-commit install-hooks
```

### Skip Hooks (Emergency)

```bash
# Skip hooks for one commit
git commit --no-verify -m "Emergency fix"

# Disable pre-commit
pre-commit uninstall
```

---

**Last Updated:** March 2026

#!/bin/bash
# Setup global pre-commit hooks for all git repositories

set -e

echo "🌍 Setting up global pre-commit hooks..."
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit globally..."
    pip install --user pre-commit
    echo "   ✅ pre-commit installed"
else
    echo "✅ pre-commit already installed"
fi

# Create git template directory
echo ""
echo "📁 Creating git template directory..."
mkdir -p ~/.git-templates/hooks

# Configure git to use template
echo ""
echo "⚙️  Configuring git to use template..."
git config --global init.templateDir ~/.git-templates
echo "   ✅ Git template configured"

# Create pre-commit hook script
echo ""
echo "📝 Creating global pre-commit hook..."
cat > ~/.git-templates/hooks/pre-commit << 'HOOKEOF'
#!/bin/bash
# Auto-install and run pre-commit if config exists

if [ -f ".pre-commit-config.yaml" ]; then
    # Check if pre-commit is installed
    if ! command -v pre-commit &> /dev/null; then
        echo "⚠️  pre-commit not installed. Install with: pip install pre-commit"
        exit 0
    fi

    # Install pre-commit hooks if not already installed
    if [ ! -f ".git/hooks/pre-commit" ] || ! grep -q "pre-commit" ".git/hooks/pre-commit" 2>/dev/null; then
        echo "📦 Installing pre-commit hooks for this repo..."
        pre-commit install --overwrite
    fi

    # Run pre-commit
    pre-commit run
else
    # No config, allow commit
    exit 0
fi
HOOKEOF

# Make executable
chmod +x ~/.git-templates/hooks/pre-commit
echo "   ✅ Global hook created"

# Apply to current repo if in one
if [ -d ".git" ]; then
    echo ""
    read -p "📍 Apply to current repository? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git init  # Re-init to apply template (safe)
        echo "   ✅ Applied to current repo"
    fi
fi

echo ""
echo "✅ Global setup complete!"
echo ""
echo "📝 What this does:"
echo "   • All new 'git init' or 'git clone' repos automatically get pre-commit hooks"
echo "   • Hooks check for .pre-commit-config.yaml in each repo"
echo "   • If found, runs pre-commit automatically before commits"
echo "   • If not found, allows commit (backward compatible)"
echo ""
echo "🔧 Apply to existing repos:"
echo "   cd /path/to/repo && git init"
echo ""
echo "📚 See docs/GLOBAL_PRECOMMIT_SETUP.md for more options"

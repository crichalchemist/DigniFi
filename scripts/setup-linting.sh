#!/bin/bash
# Setup script for code quality tools and pre-commit hooks

set -e  # Exit on error

echo "🔧 Setting up code quality tools for DigniFi..."

# Check if we're in the project root
if [ ! -f ".pre-commit-config.yaml" ]; then
    echo "❌ Error: Run this script from the project root directory"
    exit 1
fi

# Install pre-commit (Python)
echo ""
echo "📦 Installing pre-commit..."
if command -v docker-compose &> /dev/null; then
    echo "   Using Docker..."
    docker-compose exec backend pip install pre-commit black ruff
else
    echo "   Using local Python..."
    pip install pre-commit black ruff
fi

# Install Git hooks
echo ""
echo "🪝 Installing Git hooks..."
pre-commit install
echo "   ✅ Pre-commit hooks installed"

# Install frontend dependencies
echo ""
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..
echo "   ✅ Prettier installed"

# Run on all files (optional but recommended)
echo ""
echo "🎨 Running formatters on all existing files..."
read -p "   Format all files now? This may create a large diff. (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   Formatting all files..."
    pre-commit run --all-files || true
    echo "   ✅ Files formatted (review changes before committing)"
else
    echo "   ⏭️  Skipped formatting. Run 'pre-commit run --all-files' manually later."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Review docs/LINTING_SETUP.md for usage"
echo "   2. Test: Make a small change and run 'git commit'"
echo "   3. Hooks will run automatically on every commit"
echo ""
echo "🔧 Manual commands:"
echo "   Frontend: cd frontend && npm run format"
echo "   Backend:  cd backend && black . && ruff check --fix ."
echo "   All:      pre-commit run --all-files"

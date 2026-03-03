# Contributing to Shopping Truth Agent

First off, thank you for considering contributing to Shopping Truth Agent! 🎉

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues. When you create a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Screenshots** (if applicable)
- **Environment details** (Python version, OS, etc.)

### 💡 Suggesting Features

Feature suggestions are welcome! Please provide:

- **Clear use case** — Why is this feature needed?
- **Proposed solution** — How should it work?
- **Alternatives considered** — What other approaches did you think about?

### 🔧 Pull Requests

1. **Fork** the repo
2. **Create a branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test thoroughly** — Make sure nothing breaks
5. **Commit** with clear messages (`git commit -m 'Add amazing feature'`)
6. **Push** to your fork (`git push origin feature/amazing-feature`)
7. **Open a PR** with description of changes

### 📝 Coding Standards

- **Python:** Follow PEP 8
- **Docstrings:** Use Google-style docstrings
- **Type hints:** Add type annotations where possible
- **Comments:** Explain **why**, not **what**

### ✅ Testing

Before submitting:

```bash
# Run tests (when available)
pytest tests/

# Test manually
python -m agent.scrapers  # Test scraping
python -m agent.analyzers # Test analysis
```

### 📚 Documentation

- Update README.md if you change functionality
- Add/update docstrings for new functions
- Update ARCHITECTURE.md if you change structure

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/shopping-agent-marketplace.git
cd shopping-agent-marketplace

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (optional)
pip install pytest black flake8
```

## Code Review Process

- PRs require at least 1 approval
- Maintainers will review within 48 hours
- Be patient and responsive to feedback

## Community

- Be respectful and inclusive
- Help others when you can
- Celebrate successes 🎉

## Questions?

Open an issue or contact: sujal@nextbase.solutions

---

**Thank you for contributing!** ❤️

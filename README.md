# 🛒 Shopping Truth Agent

AI-powered shopping advisor for Nextbase Agent Marketplace that analyzes products across 9+ platforms, detects fake reviews, predicts price drops, and provides honest buying advice.

## 🎯 Features

- ✅ **Multi-platform analysis** — Amazon, Reddit, YouTube, Twitter
- ✅ **Fake review detection** — Pattern-based ML identifies suspicious reviews  
- ✅ **Regret detector** — Analyzes review timelines to spot quality decline
- ✅ **Confidence scoring** — Weighted by source reliability (Reddit 30%, YouTube 25%, etc.)
- ✅ **LLM-powered verdict** — Clear BUY / WAIT / AVOID recommendation
- ✅ **Zero extra API keys** — No Reddit API, no YouTube API, just your LLM key

## 📦 Installation

### For Nextbase Marketplace Backend:

```bash
# Clone this repo
git clone <your-repo-url>
cd shopping-agent-marketplace

# Copy agent files to your backend
cp -r agent/* /path/to/your/nextbase-backend/app/agents/shopping_agent/

# Install dependencies
pip install httpx beautifulsoup4

# Reload agents
curl -X POST https://your-backend.railway.app/admin/agents/reload \
  -H "X-Admin-Secret: your-admin-secret"
```

### For OpenClaw Users:

```bash
# Install from marketplace
/agent install shopping-agent

# Set your API key
export OPENAI_API_KEY=sk-xxx

# Test it
Analyze this product: https://amazon.com/dp/B08N5WRWNW
```

## 🏗 Architecture

```
User Query → Scrape Amazon + Reddit + YouTube + Twitter (parallel)
           → Analyze fake reviews + regret patterns
           → Generate LLM summary
           → Return verdict (BUY / WAIT / AVOID)
```

## 📂 File Structure

```
agent/
├── manifest.json          # Agent metadata
├── constants.py           # Configuration & weights
├── scrapers.py            # Web scraping (API-free)
├── analyzers.py           # Fake reviews, regret, confidence
├── summarizer.py          # LLM summary generation
├── executor.py            # Main orchestrator
└── SKILL.md               # OpenClaw integration guide

docs/
├── DEPLOYMENT.md          # Complete deployment guide
├── QUICKSTART.md          # 3-step quickstart
└── ARCHITECTURE.md        # Technical deep dive
```

## 🧪 Testing

```bash
# From OpenClaw
Analyze this product: https://amazon.com/dp/B08N5WRWNW

# From curl
curl -X POST https://your-backend.railway.app/v1/agents/shopping-agent/execute \
  -H "Content-Type: application/json" \
  -H "X-User-LLM-Key: $OPENAI_API_KEY" \
  -d '{"prompt": "https://amazon.com/dp/B08N5WRWNW"}'
```

## 💰 Monetization

**Free Tier:**  
- 10 analyses per day  
- Amazon + Reddit only  

**Premium ($9.99/month):**  
- Unlimited analyses  
- All features unlocked  

**Expected Revenue:** $500-2000/month

## 🚀 Roadmap

### Phase 1 (MVP - ✅ Complete)
- Amazon + Reddit + YouTube + Twitter scraping
- Fake review detection
- Regret detector
- Confidence scoring
- LLM summary

### Phase 2 (Next)
- Price prediction (historical data + ML)
- Coupon finder (auto-discover discount codes)
- Alternative product recommendations

### Phase 3
- Battle Mode (AI agents debate pros/cons)
- Carbon footprint calculator
- Ethics scoring (labor practices)

## 🛠 Tech Stack

- **Language:** Python 3.10+
- **Framework:** FastAPI (Nextbase backend)
- **Scraping:** httpx, BeautifulSoup4
- **LLM:** OpenAI GPT-4 / Claude (user's key)
- **Caching:** Redis (optional)

## 📝 Requirements

```
httpx>=0.25.0
beautifulsoup4>=4.12.0
```

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🔗 Links

- **Nextbase Marketplace:** https://agents.nextbase.solutions
- **OpenClaw:** https://openclaw.ai
- **Documentation:** See `docs/` folder

## 📧 Support

For issues or questions:
- Open a GitHub issue
- Contact marketplace support
- Email: support@nextbase.solutions

---

**Built with ❤️ for the Nextbase Agent Marketplace**

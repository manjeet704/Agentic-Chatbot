# 🤖 Setting Up Local AI with Ollama (Free, No API Key Needed)

Ollama lets you run powerful AI models like LLaMA 3.2 completely offline on your laptop.

---

## Step 1: Install Ollama

### Windows
Download and run the installer:
👉 https://ollama.com/download/windows

### Mac
```bash
brew install ollama
```
Or download from: https://ollama.com/download/mac

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

---

## Step 2: Download a Model

Open a **new terminal** and run ONE of these (choose based on your RAM):

| RAM  | Command | Quality |
|------|---------|---------|
| 4 GB | `ollama pull llama3.2:1b` | Good |
| 8 GB | `ollama pull llama3.2` | **Recommended** |
| 16 GB| `ollama pull llama3.1:8b` | Excellent |
| 32 GB| `ollama pull llama3.1:70b` | Best |

**Recommended (8 GB RAM):**
```bash
ollama pull llama3.2
```
This downloads ~2 GB. Wait for it to finish.

---

## Step 3: Start Ollama Server

```bash
ollama serve
```
Keep this terminal open. Ollama runs on http://localhost:11434

---

## Step 4: Start the Chatbot

In a **different terminal**, from the project folder:
```bash
python backend/app.py
```

Open browser: **http://localhost:5000**

---

## Using a Different Model

If you downloaded a different model, set it before starting:

**Windows:**
```cmd
set OLLAMA_MODEL=llama3.2:1b
python backend/app.py
```

**Mac/Linux:**
```bash
OLLAMA_MODEL=llama3.2:1b python backend/app.py
```

---

## Troubleshooting

**Ollama not found?** Restart your terminal after installation.

**Model download slow?** LLaMA 3.2 is ~2 GB. Use a faster connection or try the 1b model first.

**Out of memory?** Use the 1b model: `ollama pull llama3.2:1b`

**Still not working?** The chatbot works WITHOUT Ollama too — it uses a smart built-in engine. Ollama just makes it smarter and more conversational.

---

## Alternative: Use Anthropic API Key (Cloud)

If you have an Anthropic API key:

**Windows:**
```cmd
set ANTHROPIC_API_KEY=sk-ant-your-key-here
python backend/app.py
```

**Mac/Linux:**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
python backend/app.py
```

Get a key at: https://console.anthropic.com

# 🤖 Agentic Resume Optimizer

An AI-powered Streamlit app that analyzes job descriptions and optimizes your LaTeX resume using Groq or Google Gemini LLM APIs.

## Features

- 📊 **Job Analysis**: Automatically extracts key requirements, skills, and technologies from job descriptions
- 💡 **Smart Suggestions**: AI agent generates 6-8 targeted resume improvements
- ✏️ **Review & Edit**: Accept, modify, or reject suggestions with an interactive UI
- 📥 **LaTeX Output**: Download optimized resume in LaTeX format
- 🍪 **Persistent Storage**: API keys saved securely in browser cookies (no re-entry needed)
- 🤖 **Multi-LLM Support**: Choose between Groq (llama-3.3-70b-versatile) or Google Gemini (gemini-2.0-flash)
- 🔒 **Privacy First**: Your API keys stay in your browser - never stored on any server

## Setup

### 1. Clone & Install

```bash
cd resume-optimizer
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)

**Option 1: Browser Storage (Recommended for deployed app)**
- Enter your API key directly in the app UI
- Keys are saved securely in browser cookies (encrypted)
- No re-entry needed across sessions
- Works on any deployment (Streamlit Cloud, etc.)

**Option 2: Local .env file (For local development)**
Create a `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env
```

Edit `.env` and add your API key(s):

```
# For Groq (free tier available)
GROQ_API_KEY=your_actual_groq_api_key_here

# For Google Gemini (optional)
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

**Get your free API keys:**
- Groq: [console.groq.com/keys](https://console.groq.com/keys)
- Gemini: [aistudio.google.com](https://aistudio.google.com)

> **Note**: Browser cookies persist across sessions. Use the "Clear Saved Keys" button to remove stored keys.

### 3. Run the App

```bash
source venv/bin/activate
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

1. **Setup**: 
   - Select your preferred LLM provider (Groq or Gemini)
   - Enter your API key (saved securely in browser) OR it auto-loads from `.env` if present
   - Your choice and keys persist across sessions via encrypted cookies
2. **Upload**: Provide your LaTeX resume (.tex) and optionally a CV context file (.txt)
3. **Job Description**: Paste the job description you're targeting
4. **Analyze**: AI analyzes the job requirements
5. **Review**: Review AI suggestions - accept, modify, or reject each one
6. **Download**: Get your optimized LaTeX resume

**Privacy & Security:**
- API keys are encrypted and stored only in your browser
- Keys never leave your machine (not sent to any server except the LLM APIs)
- Use "Clear Saved Keys" button to remove stored credentials anytime

## Project Structure

```
resume-optimizer/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env                   # API keys (not committed to git)
├── .env.example          # Template for .env
├── .gitignore            # Git ignore rules
├── my_cv_context.txt     # Optional CV context
└── README.md             # This file
```

## Requirements

- Python 3.12+
- Groq API key OR Google Gemini API key (free tiers available)
- LaTeX resume file

## Tech Stack

- **Streamlit**: Web UI framework
- **Groq**: LLM API (using llama-3.3-70b-versatile model)
- **Google Gemini**: LLM API (using gemini-2.0-flash model)
- **streamlit-cookies-manager**: Encrypted browser storage for API keys
- **python-dotenv**: Environment variable management (optional)

## Troubleshooting

### "ModuleNotFoundError"
Make sure you've activated the virtual environment:
```bash
source venv/bin/activate
streamlit run app.py
```

### "Connection error"
- Check your internet connection
- Verify your API key is correct in `.env`
- Ensure you have API quota available

### API Key Issues
- **Browser Storage**: Keys entered in the UI are saved in encrypted browser cookies
- **Persistence**: Keys remain saved across sessions (no re-entry needed)
- **Clear Keys**: Use the "Clear Saved Keys" button to remove stored credentials
- **Local .env**: Optional fallback - app checks cookies first, then `.env`
- **Provider Switching**: Your provider choice is also saved in cookies
- **Privacy**: Never commit `.env` to version control (it's in `.gitignore`)
- **Deployment**: When deploying, users enter their own API keys (BYOK model)

## Deployment to Streamlit Cloud

### Prerequisites
1. Push your code to GitHub
2. Sign up for [Streamlit Cloud](https://streamlit.io/cloud) (free tier available)

### Steps

1. **Connect GitHub Repository**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your GitHub repository
   - Choose `main` branch
   - Set main file path: `app.py`

2. **Configure Secrets**
   - Click "Advanced settings"
   - In the "Secrets" section, add:
   ```toml
   COOKIES_PASSWORD = "your-secure-random-password-min-32-chars"
   GRPC_VERBOSITY = "ERROR"
   GLOG_minloglevel = "2"
   ```
   - Generate a strong password for `COOKIES_PASSWORD` (at least 32 characters)

3. **Deploy**
   - Click "Deploy!"
   - Wait 2-3 minutes for deployment
   - Your app will be live at `https://your-app-name.streamlit.app`

### Important Notes for Deployment

- ✅ **No API Keys Needed**: Users provide their own Groq/Gemini API keys via the UI
- ✅ **Cookie Encryption**: The `COOKIES_PASSWORD` secret encrypts user API keys in their browser
- ✅ **PDF Generation**: Will NOT work on Streamlit Cloud (no pdflatex), but LaTeX download works fine
- ✅ **Privacy**: API keys are stored only in users' browsers, never on the server

### Post-Deployment

After deployment, users can:
1. Enter their own API key (from Groq or Gemini)
2. Upload their LaTeX resume
3. Paste a job description
4. Get AI-powered optimization suggestions
5. Download the optimized LaTeX file
6. Compile to PDF (locally with pdflatex, or upload to Overleaf)

**Note**: On Streamlit Cloud (no pdflatex), users download the `.tex` file and can easily compile it on [Overleaf.com](https://www.overleaf.com) (free, online LaTeX editor).

## License

MIT
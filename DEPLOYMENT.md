# Streamlit Cloud Deployment Checklist

## ✅ Pre-Deployment

- [ ] All code committed to GitHub
- [ ] `.env` file is in `.gitignore` (not committed)
- [ ] `requirements.txt` is up to date
- [ ] `.streamlit/config.toml` is committed
- [ ] `.streamlit/secrets.toml` is NOT committed (in .gitignore)

## 🚀 Deployment Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for Streamlit Cloud deployment"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Select your repository: `mhitjain/resume-optimizer`
   - Branch: `main`
   - Main file: `app.py`
   - Click "Advanced settings"

3. **Configure Secrets**
   In the Secrets section, paste:
   ```toml
   COOKIES_PASSWORD = "generate-a-secure-32-char-password-here"
   GRPC_VERBOSITY = "ERROR"
   GLOG_minloglevel = "2"
   ```
   
   **How to generate COOKIES_PASSWORD:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

4. **Deploy**
   - Click "Deploy!"
   - Wait 2-3 minutes
   - Your app will be live!

## 📋 Post-Deployment

- [ ] Test the app with a test API key
- [ ] Verify cookie persistence works
- [ ] Test both Groq and Gemini providers
- [ ] Confirm LaTeX download works
- [ ] Note: PDF generation will NOT work (pdflatex not available on cloud)

## 🔒 Security Notes

- ✅ Users provide their own API keys (BYOK model)
- ✅ API keys stored in encrypted browser cookies only
- ✅ No API keys stored on server
- ✅ COOKIES_PASSWORD is secret (encrypts cookies)

## 🐛 Troubleshooting

**If app crashes on startup:**
- Check secrets are properly formatted (TOML syntax)
- Verify all dependencies in requirements.txt

**If cookies don't persist:**
- Ensure COOKIES_PASSWORD secret is set
- Check browser allows cookies

**If API calls fail:**
- Users need to enter valid API keys
- Check API quota limits

## 📦 Files Needed for Deployment

✅ `app.py` - Main application
✅ `requirements.txt` - Python dependencies
✅ `.streamlit/config.toml` - Streamlit configuration
✅ `.gitignore` - Excludes sensitive files
✅ `README.md` - Documentation
✅ `packages.txt` - System dependencies (empty, pdflatex not available)

**NOT included (intentionally):**
❌ `.env` - Local secrets only
❌ `.streamlit/secrets.toml` - Set via Streamlit Cloud UI
❌ `venv/` - Virtual environment (local only)

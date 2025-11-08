# Gemini Integration - Multi-LLM Support

## Overview
Added support for Google Gemini as an alternative LLM provider alongside Groq. Users can now choose between:
- **Groq**: llama-3.3-70b-versatile model
- **Gemini**: gemini-1.5-flash model

## Changes Made

### 1. Core Architecture
- **Added `get_llm_response()` function** (lines ~35-82): Unified LLM interface that abstracts provider differences
  - Checks `st.session_state.llm_provider` to determine which API to use
  - Converts message format for Gemini compatibility (system + user messages → single formatted prompt)
  - Returns consistent response format regardless of provider

### 2. Function Updates
- **`analyze_job(job_desc)`**: Removed `api_key` parameter, now uses unified `get_llm_response()`
- **`generate_suggestions(job_analysis, latex_resume, cv_context)`**: Removed `api_key` parameter, uses unified interface
- All LLM calls now go through `get_llm_response()` for consistency

### 3. Session State Management
Added new session state variables:
```python
llm_provider: str = "groq"  # Default provider
gemini_api_key: str = ""    # Gemini API key from .env or UI
```

### 4. UI Enhancements
- **LLM Provider Selector**: Dropdown to choose between Groq and Gemini
- **Dynamic API Key Input**: Shows appropriate API key input based on selected provider
- **Provider-specific links**: Direct links to API key generation pages
  - Groq: [console.groq.com](https://console.groq.com)
  - Gemini: [aistudio.google.com](https://aistudio.google.com)

### 5. Dependencies
- **Added `google-generativeai==0.7.2`** to requirements.txt
- Compatible with existing streamlit and protobuf versions

### 6. Environment Variables
Added support for `GEMINI_API_KEY` in `.env` file:
```bash
GROQ_API_KEY=your_groq_key_here
GEMINI_API_KEY=your_gemini_key_here  # Optional
```

## Technical Details

### Message Format Conversion
Gemini requires a different message format than OpenAI-style APIs:

**Groq (OpenAI format):**
```python
messages = [
    {"role": "system", "content": "You are..."},
    {"role": "user", "content": "Analyze..."}
]
```

**Gemini (converted):**
```python
prompt = "System: You are...\n\nUser: Analyze..."
```

The `get_llm_response()` function handles this conversion automatically.

### Response Parsing
Both providers return JSON responses, but the response structure differs:
- **Groq**: `response.choices[0].message.content`
- **Gemini**: `response.text`

The unified function normalizes these differences.

## Usage

1. **Select Provider**: Choose Groq or Gemini from dropdown in UI
2. **Enter API Key**: Provide appropriate API key (or load from `.env`)
3. **Use Normally**: All features work identically with either provider

## Benefits

1. **Flexibility**: Switch providers without changing code
2. **Reliability**: Fallback option if one provider has issues
3. **Cost Optimization**: Choose based on pricing/limits
4. **Performance**: Compare quality between models
5. **Future-proof**: Easy to add more providers using same pattern

## Testing

✅ Groq integration maintained (no breaking changes)
✅ Gemini API properly configured
✅ Dependencies installed without conflicts
✅ UI displays provider selection correctly
✅ API key management works for both providers

## Future Enhancements

Potential improvements:
- Add more LLM providers (Claude, OpenAI, etc.)
- Provider-specific settings (temperature, max tokens)
- Automatic fallback if primary provider fails
- Cost/token tracking per provider
- Model selection within each provider

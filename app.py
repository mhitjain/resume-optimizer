import streamlit as st
from groq import Groq
import json
import datetime
import os
import re
from dotenv import load_dotenv
from streamlit_cookies_manager import EncryptedCookieManager

# Suppress gRPC warnings from Google API
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Agentic Resume Optimizer",
    page_icon="🤖",
    layout="wide"
)

# Initialize cookie manager for persistent storage
cookies = EncryptedCookieManager(
    prefix="resume_optimizer_",
    password=os.getenv("COOKIES_PASSWORD", "default_secure_password_change_in_production")
)

if not cookies.ready():
    st.stop()

# Initialize session state
for key in ['step', 'job_analysis', 'suggestions', 'final_latex', 'log', 'api_key', 'gemini_api_key', 'llm_provider']:
    if key not in st.session_state:
        if key == 'step':
            st.session_state[key] = 1
        elif key in ['suggestions', 'log']:
            st.session_state[key] = []
        elif key == 'api_key':
            # Try to load from cookies first, then .env
            st.session_state[key] = cookies.get('groq_api_key') or os.getenv('GROQ_API_KEY', '')
        elif key == 'gemini_api_key':
            # Try to load from cookies first, then .env
            st.session_state[key] = cookies.get('gemini_api_key') or os.getenv('GEMINI_API_KEY', '')
        elif key == 'llm_provider':
            st.session_state[key] = cookies.get('llm_provider') or 'groq'
        else:
            st.session_state[key] = None

def add_log(message, type='info'):
    """Add entry to agent log"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    st.session_state.log.append({
        'message': message,
        'type': type,
        'time': timestamp
    })

def get_llm_response(messages, temperature=0.5, max_tokens=4000):
    """Get LLM response from selected provider (Groq or Gemini)"""
    provider = st.session_state.llm_provider
    
    if provider == 'groq':
        api_key = st.session_state.api_key
        if not api_key:
            raise ValueError("Groq API key not provided")
        
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    elif provider == 'gemini':
        api_key = st.session_state.gemini_api_key
        if not api_key:
            raise ValueError("Gemini API key not provided")
        
        # Clean the API key (remove whitespace)
        api_key = api_key.strip()
        
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # Convert messages to Gemini format
        # Use gemini-2.0-flash which is stable and fast
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Combine system and user messages for Gemini
        prompt_parts = []
        for msg in messages:
            if msg['role'] == 'system':
                prompt_parts.append(f"SYSTEM INSTRUCTIONS:\n{msg['content']}\n")
            elif msg['role'] == 'user':
                prompt_parts.append(msg['content'])
        
        prompt = '\n'.join(prompt_parts)
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        return response.text
    
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

def escape_latex(text):
    """Escape special LaTeX characters"""
    if not text:
        return text
    
    # LaTeX special characters that need escaping
    replacements = {
        '\\': r'\textbackslash{}',  # Must be first
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '&': r'\&',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    
    result = text
    for char, escaped in replacements.items():
        result = result.replace(char, escaped)
    
    return result

@st.cache_data(show_spinner=False)
def compile_latex_to_pdf_online(latex_content):
    """Fallback when pdflatex is not available - provides helpful guidance"""
    
    add_log('ℹ️ PDF compilation not available without local pdflatex', 'info')
    
    st.warning("""
    📄 **PDF Compilation Not Available**
    
    Since pdflatex is not installed locally, PDF generation isn't available.
    
    **Easy Solution - Use Overleaf (Free):**
    1. Download the LaTeX file below (`.tex`)
    2. Go to [Overleaf.com](https://www.overleaf.com) (free account)
    3. Click "New Project" → "Upload Project"
    4. Upload your `.tex` file
    5. It will compile to PDF automatically!
    
    💡 **Bonus**: Overleaf lets you edit and recompile easily in your browser.
    """)
    
    return None

@st.cache_data(show_spinner=False)
def compile_latex_to_pdf(latex_content):
    """Compile LaTeX to PDF using pdflatex (local) or online API (cloud)"""
    import subprocess
    import tempfile
    import shutil
    
    add_log('📄 Compiling LaTeX to PDF...', 'info')
    
    # Check if pdflatex is available (local installation)
    pdflatex_paths = [
        '/Library/TeX/texbin/pdflatex',  # MacTeX default
        '/usr/local/texlive/2024/bin/universal-darwin/pdflatex',  # Manual install
        '/usr/local/texlive/2025/bin/universal-darwin/pdflatex',  # Newer version
        shutil.which('pdflatex')  # In PATH
    ]
    
    pdflatex_cmd = None
    for path in pdflatex_paths:
        if path and os.path.exists(path):
            pdflatex_cmd = path
            break
    
    if not pdflatex_cmd:
        # Try to find it with which command
        try:
            result = subprocess.run(['which', 'pdflatex'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                pdflatex_cmd = result.stdout.strip()
        except:
            pass
    
    # If no local pdflatex, show Overleaf instructions
    if not pdflatex_cmd:
        add_log('ℹ️ Local pdflatex not found - use Overleaf for PDF generation', 'info')
        return compile_latex_to_pdf_online(latex_content)
    
    # Use local pdflatex if available
    try:
        # Clean the LaTeX content - remove any text before \documentclass
        import re
        match = re.search(r'\\documentclass', latex_content)
        if match:
            latex_content = latex_content[match.start():]
        
        # Remove markdown code blocks if present
        latex_content = latex_content.replace('```latex', '').replace('```', '').strip()
        
        # Create a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write LaTeX content to file
            tex_file = os.path.join(tmpdir, "resume.tex")
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            
            # Set up environment with proper PATH
            env = os.environ.copy()
            if '/Library/TeX/texbin' not in env.get('PATH', ''):
                env['PATH'] = '/Library/TeX/texbin:' + env.get('PATH', '')
            
            # Run pdflatex twice (for proper references)
            for _ in range(2):
                result = subprocess.run(
                    [pdflatex_cmd, '-interaction=nonstopmode', '-output-directory', tmpdir, tex_file],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env=env
                )
            
            pdf_file = os.path.join(tmpdir, "resume.pdf")
            
            if os.path.exists(pdf_file):
                # Read the PDF
                with open(pdf_file, 'rb') as f:
                    pdf_data = f.read()
                add_log('✅ PDF compiled successfully!', 'success')
                return pdf_data
            else:
                error_msg = "PDF compilation failed. Check LaTeX syntax."
                if result.stderr:
                    error_msg += f"\n{result.stderr[:500]}"
                add_log(f'❌ {error_msg}', 'error')
                st.error(f"LaTeX Error: {result.stderr[:200] if result.stderr else 'Unknown error'}")
                return None
                
    except Exception as e:
        add_log(f'❌ PDF compilation failed: {str(e)}', 'error')
        st.error(f"PDF compilation error: {str(e)}")
        return None

@st.cache_data(show_spinner=False)
def get_pdf_download_data(pdf_bytes):
    """Wrapper function to cache PDF data for download button"""
    return pdf_bytes

def analyze_job(job_desc):
    """Step 1: Agent analyzes job description"""
    add_log('🧠 Agent analyzing job description...', 'info')
    
    try:
        messages = [{
            "role": "system",
            "content": "You are a resume expert. Return ONLY valid JSON, no markdown."
        }, {
            "role": "user",
            "content": f"""Analyze this job description:

{job_desc}

Return ONLY this JSON structure (no markdown, no code blocks):
{{
  "role_type": "backend/frontend/fullstack/data",
  "top_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "required_technologies": ["tech1", "tech2", "tech3"],
  "valued_metrics": ["metric1", "metric2"],
  "key_responsibilities": ["resp1", "resp2"],
  "company_values": ["value1", "value2"],
  "experience_level": "junior/mid/senior"
}}"""
        }]
        
        content = get_llm_response(messages, temperature=0.3, max_tokens=1000)
        
        # Remove markdown code blocks if present
        content = content.replace('```json', '').replace('```', '').strip()
        
        analysis = json.loads(content)
        add_log('✓ Job analysis complete', 'success')
        return analysis
    
    except Exception as e:
        add_log(f'❌ Analysis failed: {str(e)}', 'error')
        st.error(f"Error: {str(e)}")
        return None

def generate_suggestions(job_analysis, latex_resume, cv_context):
    """Step 2: Agent generates strategic keyword-focused suggestions with line numbers"""
    add_log('🤖 Agent analyzing keyword gaps...', 'info')
    
    try:
        # Add line numbers to resume for AI to reference
        lines = latex_resume.split('\n')
        numbered_resume = '\n'.join([f"{i+1:4d} | {line}" for i, line in enumerate(lines)])
        
        messages = [{
            "role": "system",
            "content": """You are an expert ATS resume optimizer and software engineer who understands technical context and project coherence.
Your goal: Make intelligent, contextually-appropriate modifications that enhance ATS matching while maintaining technical accuracy.
CRITICAL: Only modify existing bullets. No additions. Each modification must make technical sense."""
        }, {
            "role": "user",
            "content": f"""Analyze this resume deeply and make strategic, contextually-appropriate modifications.

=== JOB REQUIREMENTS ===
Role: {job_analysis.get('role', 'Not specified')}
Required Skills: {', '.join(job_analysis.get('required_skills', [])[:15])}
Required Technologies: {', '.join(job_analysis.get('required_technologies', [])[:15])}
Key Responsibilities: {', '.join(job_analysis.get('key_responsibilities', [])[:8])}

=== RESUME WITH LINE NUMBERS ===
{numbered_resume}

=== CANDIDATE BACKGROUND (Use for authenticity) ===
{cv_context or 'No additional context provided'}

=== INTELLIGENT ANALYSIS PROCESS ===

STEP 1 - UNDERSTAND THE RESUME STRUCTURE:
For each job/project section:
- What is the role/company? (e.g., "Data & AI Engineer Intern at TekLink")
- What technologies does this role logically use? (e.g., Azure for cloud roles, React for frontend)
- What are the main achievements in this section?
- Which bullets are strongest (have metrics, clear impact)?
- Which bullets are weakest (generic, no metrics, low relevance)?

STEP 2 - IDENTIFY MISSING KEYWORDS STRATEGICALLY:
- Which required technologies are COMPLETELY missing from the entire resume?
- For each missing technology, ask: "Where would this naturally fit?"
  * Backend role → Can add databases, APIs, frameworks
  * Cloud role → Can add cloud services, DevOps tools
  * Frontend role → Can add UI libraries, state management
- DON'T force unrelated keywords (e.g., don't add Kubernetes to a pure frontend bullet)

STEP 3 - FIND LOW-VALUE BULLETS TO REPLACE:
Prioritize bullets that are:
- Generic without specific technologies (e.g., "Improved system performance")
- Missing metrics or quantifiable impact
- Using outdated/less relevant technologies for this job
- Duplicate achievements (saying same thing as another bullet)
- Least aligned with the job requirements

STEP 4 - MAKE CONTEXTUALLY-SMART MODIFICATIONS:
For each modification:

✅ GOOD PRACTICES:
- **Technical Coherence**: Only add technologies that logically work together
  * Example: "React + TypeScript + Node.js" ✓ (full-stack makes sense)
  * Example: "Kubernetes + SQL + React" ✗ (too scattered, doesn't tell a story)
  
- **Role-Appropriate**: Match technologies to the role context
  * Cloud Engineer role → Add AWS/Azure services, Terraform, Docker
  * Backend role → Add Spring Boot, PostgreSQL, REST APIs, Kafka
  * Data role → Add ETL tools, data pipelines, analytics platforms
  
- **Natural Integration**: Keywords should flow naturally in the sentence
  * Good: "Built scalable microservices using Spring Boot, PostgreSQL, and Redis"
  * Bad: "Built microservices using Spring Boot, Kubernetes, Machine Learning, Blockchain"
  
- **Preserve Authenticity**: Only add tech that fits the candidate's background
  * Check CV context - does candidate have experience with this?
  * Don't add senior-level tech to junior roles
  
- **Maintain Technical Story**: Each bullet should tell a coherent technical story
  * Problem → Solution → Technologies Used → Impact/Metrics

❌ BAD PRACTICES:
- Keyword stuffing: cramming unrelated technologies together
- Technology mismatches: adding frontend tech to backend bullets
- Breaking technical logic: adding incompatible tool combinations
- Making bullets longer just to add keywords
- Replacing strong, relevant bullets with weaker ones

STEP 5 - PRIORITIZATION LOGIC:
Choose bullets to modify using this priority:
1. **HIGH PRIORITY**: Generic bullets with no specific tech that can naturally incorporate missing keywords
2. **MEDIUM PRIORITY**: Bullets with outdated tech that can be updated to required tech
3. **LOW PRIORITY**: Strong bullets that just need minor keyword additions
4. **NEVER**: Don't touch bullets that already perfectly match job requirements

=== CONTEXTUAL EXAMPLES ===

GOOD MODIFICATION (Backend role missing PostgreSQL, Redis):
BEFORE: "Developed user authentication system with secure session management"
AFTER: "Developed user authentication system with PostgreSQL, Redis caching, and JWT-based session management"
Why: Naturally adds database + caching technologies that fit authentication context

BAD MODIFICATION (Don't do this):
BEFORE: "Created React dashboard for analytics"
AFTER: "Created React dashboard using Kubernetes, PostgreSQL, and Kafka for analytics"
Why: Kubernetes/Kafka don't belong in a frontend dashboard bullet - not coherent

GOOD MODIFICATION (Cloud role missing specific AWS services):
BEFORE: "Deployed applications to cloud infrastructure"
AFTER: "Deployed applications to AWS using EC2, Lambda, and S3 with automated CI/CD"
Why: Adds specific, related AWS services that logically work together

=== OUTPUT FORMAT ===
Return ONLY valid JSON (no markdown, no code blocks):

[
  {{
    "line_number": 142,
    "action": "modify",
    "current_text": "         \\resumeItem{{Built Java microservices with Spring Boot}}",
    "suggested_text": "         \\resumeItem{{Built Java 8/Spring Boot microservices with PostgreSQL and Redis caching}}",
    "reasoning": "This bullet was weak/generic. Added missing keywords [Java 8, PostgreSQL, Redis] which logically fit this backend context. Original bullet had no database tech. New version tells coherent technical story.",
    "impact": "high",
    "keywords_added": ["Java 8", "PostgreSQL", "Redis"]
  }}
]

CRITICAL - FORMATTING RULES:
⚠️ BOTH current_text AND suggested_text MUST be COMPLETE, EXACT COPIES of the full line including:
   - ALL leading spaces (indentation)
   - The \\resumeItem{{ command
   - The closing }}
   - ANY trailing characters

EXAMPLE - What you see in numbered resume:
Line 142: "         \\resumeItem{{Built microservices}}"

YOUR JSON MUST BE:
{{
  "current_text": "         \\resumeItem{{Built microservices}}",
  "suggested_text": "         \\resumeItem{{Built Spring Boot microservices with PostgreSQL}}"
}}

Notice:
✓ Both have 9 leading spaces (copy from original)
✓ Both have \\resumeItem{{ and }}
✓ Only the text INSIDE the {{}} changed

CRITICAL RULES:
1. ONLY use action: "modify" (never "add_after" or "remove")
2. Return 4-6 modifications maximum - choose the WEAKEST/MOST GENERIC bullets
3. Every suggestion must be "high" impact
4. Focus on \\resumeItem{{ lines (work experience bullets)
5. **TECHNICAL COHERENCE**: Only add technologies that logically work together in that context
6. **CONTEXTUAL FIT**: Match technologies to the role type (backend/frontend/cloud/data)
7. EXACT line_number from resume (double-check!)
8. Copy COMPLETE LINE for current_text (all spaces, \\resumeItem{{, }})
9. Copy COMPLETE LINE for suggested_text (all spaces, \\resumeItem{{, }}, just change text inside)
10. Use SINGLE backslash: "\\resumeItem" not "\\\\resumeItem"
11. Don't make bullets longer - same length or shorter
12. **PRIORITIZE WEAK BULLETS**: Choose bullets that are generic, have no specific tech, or are least relevant to the job

Return ONLY the JSON array."""
        }]
        
        content = get_llm_response(messages, temperature=0.5, max_tokens=4000)
        
        # Clean markdown and extra text
        content = re.sub(r'^```json\n?', '', content)
        content = re.sub(r'^```\n?', '', content)
        content = re.sub(r'\n?```$', '', content)
        content = content.strip()
        
        # Extract JSON if there's extra text
        if not content.startswith('['):
            start_idx = content.find('[')
            if start_idx > 0:
                add_log(f'⚠️ Removing extra text before JSON', 'warning')
                content = content[start_idx:]
        
        if not content.endswith(']'):
            end_idx = content.rfind(']')
            if end_idx > 0:
                add_log(f'⚠️ Removing extra text after JSON', 'warning')
                content = content[:end_idx + 1]
        
        # Parse JSON - handle LaTeX escape sequences
        try:
            # First, try raw string decode to preserve backslashes
            suggestions = json.loads(content, strict=False)
        except json.JSONDecodeError as json_err:
            # If that fails, try escaping backslashes properly
            try:
                # Replace single backslash with double backslash for JSON parsing
                content_escaped = content.replace('\\', '\\\\')
                suggestions = json.loads(content_escaped, strict=False)
                add_log(f'⚠️ Had to escape backslashes for JSON parsing', 'warning')
            except json.JSONDecodeError as second_err:
                add_log(f'❌ JSON parse error: {str(json_err)}', 'error')
                st.error("Failed to parse suggestions. Please try again.")
                with st.expander("Debug: Raw AI Response"):
                    st.code(content, language="text")
                return None
        
        # Validate structure
        if not isinstance(suggestions, list):
            st.error("Expected a list of suggestions")
            return None
        
        # Filter out any non-modify suggestions (enforce modifications only)
        original_count = len(suggestions)
        suggestions = [s for s in suggestions if s.get('action') == 'modify']
        if len(suggestions) < original_count:
            filtered = original_count - len(suggestions)
            add_log(f'⚠️ Filtered out {filtered} non-modify suggestions (only modifications allowed)', 'warning')
        
        # Add status tracking
        for s in suggestions:
            s['status'] = 'pending'
            s['modified_text'] = s.get('suggested_text', '')
        
        add_log(f'✅ Generated {len(suggestions)} suggestions', 'success')
        return suggestions
    
    except Exception as e:
        add_log(f'❌ Failed: {str(e)}', 'error')
        st.error(f"Error: {str(e)}")
        return None

def apply_changes_by_line(latex_resume, approved_suggestions):
    """Step 3: Apply approved changes using line numbers (100% accurate!)"""
    add_log(f'🔧 Applying {len(approved_suggestions)} changes by line number...', 'info')
    
    try:
        import re
        lines = latex_resume.split('\n')
        changes_made = []
        
        # Sort suggestions by line number in reverse order
        # This ensures that adding/removing lines doesn't affect line numbers of earlier changes
        sorted_suggestions = sorted(approved_suggestions, key=lambda x: x['line_number'], reverse=True)
        
        for suggestion in sorted_suggestions:
            line_num = suggestion['line_number'] - 1  # Convert to 0-indexed
            action = suggestion['action']
            
            # Validate line number
            if line_num < 0 or line_num >= len(lines):
                add_log(f"⚠️ Invalid line number: {line_num + 1}", 'warning')
                continue
            
            original_line = lines[line_num]
            
            if action == 'modify':
                # Get the modified text - it should already have LaTeX formatting from AI
                suggested_text = suggestion.get('modified_text', '').strip()
                
                if not suggested_text:
                    add_log(f"⚠️ Empty suggestion for line {line_num + 1}, skipping", 'warning')
                    continue
                
                # The AI should provide the complete line with LaTeX formatting and indentation
                # Simply replace the line with what the AI provided
                lines[line_num] = suggested_text
                
                changes_made.append(f"Modified line {line_num + 1}")
                add_log(f"✓ Modified line {line_num + 1}", 'success')
            
            elif action == 'remove':
                # Remove the line
                lines[line_num] = None  # Mark for removal
                changes_made.append(f"Removed line {line_num + 1}")
                add_log(f"✓ Removed line {line_num + 1}", 'success')
            
            elif action == 'add_after':
                # This should not happen with new constraints, but keep for safety
                add_log(f"⚠️ Skipping 'add_after' action - only modifications allowed", 'warning')
                continue
        
        # Remove None entries (deleted lines)
        lines = [line for line in lines if line is not None]
        
        modified_resume = '\n'.join(lines)
        add_log(f'✅ Applied {len(changes_made)} changes successfully!', 'success')
        return modified_resume
    
    except Exception as e:
        add_log(f'❌ Failed: {str(e)}', 'error')
        st.error(f"Error: {str(e)}")
        return None
    """Step 3: Apply approved changes using direct string replacement"""
    add_log(f'🔧 Applying {len(approved_suggestions)} changes...', 'info')
    
    try:
        import re
        modified_resume = latex_resume
        changes_made = []
        
        for suggestion in approved_suggestions:
            suggestion_type = suggestion['type']
            section = suggestion['section']
            target = suggestion['target']
            current_text = suggestion['current_text'].strip()
            modified_text = escape_latex(suggestion['modified_text']) if suggestion['modified_text'] else ""
            
            # ===== HANDLE SKILLS SECTION (different format) =====
            if section == 'Skills':
                add_log(f"🔍 Processing Skills section: {target}", 'info')
                
                # Skills use: \textbf{Category}{: item1, item2, ...}
                # Try to find the specific skills category line
                category_pattern = rf'\\textbf\{{{re.escape(target)}\}}{{:\s*([^}}]+)\}}'
                match = re.search(category_pattern, modified_resume)
                
                if not match:
                    # Try fuzzy match on category name
                    fuzzy_pattern = rf'\\textbf\{{[^}}]*{re.escape(target[:15])}[^}}]*\}}{{:\s*([^}}]+)\}}'
                    match = re.search(fuzzy_pattern, modified_resume)
                
                if match:
                    if suggestion_type == 'modify':
                        # Replace the entire skills line
                        old_line = match.group(0)
                        new_line = f"\\textbf{{{target}}}{{: {modified_text}}}"
                        modified_resume = modified_resume.replace(old_line, new_line, 1)
                        changes_made.append(f"Modified Skills: {target}")
                        add_log(f"✓ Updated Skills category: {target}", 'success')
                    elif suggestion_type == 'remove':
                        # Remove entire skills line
                        old_line = match.group(0)
                        modified_resume = modified_resume.replace(old_line, "", 1)
                        changes_made.append(f"Removed Skills: {target}")
                        add_log(f"✓ Removed Skills category: {target}", 'success')
                    elif suggestion_type == 'add':
                        # Add new skills category
                        # Find the Skills section and add before the end
                        skills_section_match = re.search(r'\\section\{Skills\}.*?(?=\\section|\Z)', modified_resume, re.DOTALL)
                        if skills_section_match:
                            skills_content = skills_section_match.group(0)
                            # Add new line before the section ends
                            new_line = f"    \\textbf{{{target}}}{{: {modified_text}}} \\\\\n"
                            insert_pos = skills_section_match.end() - 1
                            modified_resume = modified_resume[:insert_pos] + new_line + modified_resume[insert_pos:]
                            changes_made.append(f"Added Skills: {target}")
                            add_log(f"✓ Added new Skills category: {target}", 'success')
                else:
                    add_log(f"⚠️ Could not find Skills category: {target}", 'info')
                continue
            
            # ===== HANDLE ADD TYPE (Work Experience/Projects) =====
            if suggestion_type == 'add':
                # Fuzzy match target company/project name
                target_pattern = re.escape(target[:30])  # Use first 30 chars for matching
                target_match = re.search(target_pattern, modified_resume)
                
                if target_match:
                    target_pos = target_match.start()
                    # Find the next \resumeItemListEnd after target
                    end_pos = modified_resume.find("\\resumeItemListEnd", target_pos)
                    if end_pos > 0:
                        new_bullet = f"\n        \\resumeItem{{{modified_text}}}"
                        modified_resume = modified_resume[:end_pos] + new_bullet + "\n      " + modified_resume[end_pos:]
                        changes_made.append(f"Added to {target}")
                        add_log(f"✓ Added bullet to {target[:40]}...", 'success')
                    else:
                        add_log(f"⚠️ Could not find insertion point for {target[:40]}...", 'info')
                else:
                    add_log(f"⚠️ Could not find target section: {target[:40]}...", 'info')
                continue
            
            # ===== HANDLE MODIFY/REMOVE (Work Experience/Projects) =====
            # Strategy: Use progressive fuzzy matching with increasing lengths
            search_pattern = None
            
            # Try exact match first
            exact_pattern = f"\\resumeItem{{{current_text}}}"
            if exact_pattern in modified_resume:
                search_pattern = exact_pattern
                add_log(f"✓ Found exact match", 'info')
            else:
                # Progressive fuzzy matching: try different substring lengths
                for length in [200, 150, 100, 70, 50, 30]:
                    if len(current_text) < length:
                        continue
                    
                    # Escape special regex chars
                    escaped_text = re.escape(current_text[:length])
                    pattern = r'\\resumeItem\{[^}]*' + escaped_text + r'[^}]*\}'
                    match = re.search(pattern, modified_resume, re.DOTALL)
                    
                    if match:
                        search_pattern = match.group(0)
                        add_log(f"✓ Found match using {length} chars", 'info')
                        break
                
                if not search_pattern:
                    # Last resort: match first few words
                    words = current_text.split()[:5]
                    if words:
                        word_pattern = r'\\resumeItem\{[^}]*' + '.*?'.join(re.escape(w) for w in words) + r'[^}]*\}'
                        match = re.search(word_pattern, modified_resume, re.DOTALL)
                        if match:
                            search_pattern = match.group(0)
                            add_log(f"✓ Found match using first {len(words)} words", 'info')
            
            if not search_pattern:
                add_log(f"⚠️ Could not find match for: {current_text[:50]}...", 'info')
                continue
            
            # Apply the change
            if suggestion_type == 'remove':
                modified_resume = modified_resume.replace(search_pattern, "", 1)
                changes_made.append(f"Removed: {current_text[:60]}...")
                add_log(f"✓ Removed bullet from {target}", 'success')
                
            elif suggestion_type == 'modify':
                replacement = f"\\resumeItem{{{modified_text}}}"
                modified_resume = modified_resume.replace(search_pattern, replacement, 1)
                changes_made.append(f"Modified in {target}")
                add_log(f"✓ Modified bullet in {target}", 'success')
        
        add_log(f'✅ Applied {len(changes_made)} changes successfully!', 'success')
        return modified_resume
    
    except Exception as e:
        add_log(f'❌ Failed: {str(e)}', 'error')
        st.error(f"Error: {str(e)}")
        return None

# ==================
# UI
# ==================

st.title("🤖 Agentic Resume Optimizer")
st.markdown("AI agent that analyzes, suggests, and optimizes your resume")

# Progress
cols = st.columns(4)
steps = ["1️⃣ Upload", "2️⃣ Analysis", "3️⃣ Review", "4️⃣ Final"]
for i, (col, label) in enumerate(zip(cols, steps), 1):
    with col:
        if st.session_state.step > i:
            st.success(f"✓ {label}")
        elif st.session_state.step == i:
            st.info(f"➤ {label}")
        else:
            st.write(f"⚪ {label}")

st.markdown("---")

# STEP 1: Upload
if st.session_state.step == 1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("⚙️ Setup")
        
        # LLM Provider Selection
        provider = st.selectbox(
            "🤖 LLM Provider",
            options=["groq", "gemini"],
            index=0 if st.session_state.llm_provider == "groq" else 1,
            key="provider_selector"
        )
        
        if provider != st.session_state.llm_provider:
            st.session_state.llm_provider = provider
            cookies['llm_provider'] = provider
            cookies.save()
            st.rerun()
        
        # Show appropriate API key based on provider
        if st.session_state.llm_provider == "groq":
            if st.session_state.api_key:
                st.success("✓ Groq API Key saved in browser")
                with st.expander("🔑 Update Groq API Key (Optional)"):
                    new_key = st.text_input("Enter new Groq API Key", type="password", key="new_groq_key")
                    if st.button("Update Groq Key"):
                        if new_key:
                            st.session_state.api_key = new_key
                            cookies['groq_api_key'] = new_key
                            cookies.save()
                            st.success("Groq API Key updated and saved!")
                            st.rerun()
            else:
                st.info("🔑 Enter your Groq API key to get started")
                api_key_input = st.text_input("Groq API Key", type="password", key="groq_key_input", 
                                               placeholder="gsk_...")
                st.caption("Get free API key from [console.groq.com](https://console.groq.com)")
                st.caption("🍪 Your key will be saved securely in your browser")
                if api_key_input:
                    st.session_state.api_key = api_key_input
                    cookies['groq_api_key'] = api_key_input
                    cookies.save()
        else:  # gemini
            if st.session_state.gemini_api_key:
                st.success("✓ Gemini API Key saved in browser")
                with st.expander("🔑 Update Gemini API Key (Optional)"):
                    new_key = st.text_input("Enter new Gemini API Key", type="password", key="new_gemini_key")
                    if st.button("Update Gemini Key"):
                        if new_key:
                            st.session_state.gemini_api_key = new_key
                            cookies['gemini_api_key'] = new_key
                            cookies.save()
                            st.success("Gemini API Key updated and saved!")
                            st.rerun()
            else:
                st.info("🔑 Enter your Gemini API key to get started")
                api_key_input = st.text_input("Gemini API Key", type="password", key="gemini_key_input",
                                               placeholder="AIza...")
                st.caption("Get free API key from [aistudio.google.com](https://aistudio.google.com)")
                st.caption("🍪 Your key will be saved securely in your browser")
                if api_key_input:
                    st.session_state.gemini_api_key = api_key_input
                    cookies['gemini_api_key'] = api_key_input
                    cookies.save()
        
        # Clear saved keys button
        st.divider()
        if st.button("🗑️ Clear Saved Keys", help="Remove all saved API keys from browser"):
            cookies['groq_api_key'] = ''
            cookies['gemini_api_key'] = ''
            cookies['llm_provider'] = ''
            cookies.save()
            st.session_state.api_key = ''
            st.session_state.gemini_api_key = ''
            st.success("All saved keys cleared!")
            st.rerun()
        
        st.subheader("📄 Files")
        latex_file = st.file_uploader("LaTeX Resume (.tex)", type=['tex'])
        cv_file = st.file_uploader("CV Context (.txt) - Optional", type=['txt'])
        
        latex_content = latex_file.read().decode() if latex_file else ""
        cv_content = cv_file.read().decode() if cv_file else ""
    
    with col2:
        st.subheader("💼 Job Description")
        job_desc = st.text_area("Paste job description", height=400)
        
        if st.button("🚀 Start Analysis", use_container_width=True, type="primary"):
            # Check for API key based on provider
            api_key_present = (
                st.session_state.api_key if st.session_state.llm_provider == "groq" 
                else st.session_state.gemini_api_key
            )
            
            if not api_key_present or not latex_content or not job_desc:
                st.error("❌ Missing inputs (API Key, Resume, or Job Description)")
            else:
                st.session_state.log = []
                
                with st.spinner("Analyzing..."):
                    analysis = analyze_job(job_desc)
                    
                    if analysis:
                        st.session_state.job_analysis = analysis
                        st.session_state.latex_content = latex_content
                        st.session_state.cv_content = cv_content
                        st.session_state.step = 2
                        st.rerun()

# STEP 2: Analysis
elif st.session_state.step == 2:
    st.subheader("📊 Job Analysis")
    
    analysis = st.session_state.job_analysis
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Role", analysis['role_type'].title())
        st.metric("Level", analysis['experience_level'].title())
    with col2:
        st.write("**Top Skills:**")
        for skill in analysis['top_skills'][:5]:
            st.write(f"• {skill}")
    
    st.write("**Technologies:**")
    st.write(", ".join(analysis['required_technologies']))
    
    st.markdown("---")
    
    if st.button("🤖 Generate Suggestions", use_container_width=True, type="primary"):
        with st.spinner("Generating..."):
            suggestions = generate_suggestions(
                analysis,
                st.session_state.latex_content,
                st.session_state.cv_content
            )
            
            if suggestions:
                st.session_state.suggestions = suggestions
                st.session_state.step = 3
                st.rerun()

# STEP 3: Review
elif st.session_state.step == 3:
    st.subheader("✨ Review Suggestions")
    
    suggestions = st.session_state.suggestions
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pending", sum(1 for s in suggestions if s['status'] == 'pending'))
    col2.metric("Accepted", sum(1 for s in suggestions if s['status'] == 'accepted'))
    col3.metric("Modified", sum(1 for s in suggestions if s['status'] == 'modified'))
    col4.metric("Rejected", sum(1 for s in suggestions if s['status'] == 'rejected'))
    
    st.markdown("---")
    
    # Each suggestion
    for i, s in enumerate(suggestions):
        status_emoji = {
            'pending': '⏳',
            'accepted': '✓',
            'modified': '✎',
            'rejected': '✗'
        }[s['status']]
        
        with st.expander(f"{status_emoji} Line {s['line_number']} - {s['action'].upper()}", 
                        expanded=(s['status'] == 'pending')):
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**Action:** {s['action']}")
            with col2:
                impact_color = {'high': '🔴', 'medium': '🟡', 'low': '⚪'}
                st.write(f"**Impact:** {impact_color[s['impact']]} {s['impact']}")
            
            # Show keywords added if available
            if s.get('keywords_added') and len(s['keywords_added']) > 0:
                st.success(f"🔑 **Keywords Added:** {', '.join(s['keywords_added'])}")
            
            # Show line number for precise location
            st.info(f"**📍 Line {s['line_number']}:** {s['current_text'][:150]}{'...' if len(s['current_text']) > 150 else ''}")
            
            # Show editable text area based on action
            if s['action'] == 'modify':
                st.write("**Suggested Text (Edit as needed):**")
                s['modified_text'] = st.text_area(
                    "Edit suggestion",
                    value=s['modified_text'],
                    key=f"mod_{s['line_number']}",
                    height=80,
                    label_visibility="collapsed",
                    help="Edit this text before accepting"
                )
            elif s['action'] == 'remove':
                st.warning("**Action:** This line will be REMOVED")
            elif s['action'] == 'add_after':
                st.success(f"**Action:** ADD new line after line {s['line_number']}")
                s['modified_text'] = st.text_area(
                    "Edit new line",
                    value=s['modified_text'],
                    key=f"mod_{s['line_number']}",
                    height=80,
                    label_visibility="collapsed",
                    help="Edit this new line before accepting"
                )
            
            st.caption(f"**Why:** {s['reasoning']}")
            
            st.markdown("---")
            
            if s['status'] == 'pending':
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✓ Accept", key=f"acc_{s['line_number']}", use_container_width=True):
                        s['status'] = 'accepted'
                        st.rerun()
                with col2:
                    if st.button("✗ Reject", key=f"rej_{s['line_number']}", use_container_width=True):
                        s['status'] = 'rejected'
                        st.rerun()
            elif s['status'] == 'accepted':
                col1, col2 = st.columns(2)
                with col1:
                    st.success("✓ Accepted")
                with col2:
                    if st.button("↺ Reset", key=f"reset_{s['line_number']}", use_container_width=True):
                        s['status'] = 'pending'
                        st.rerun()
            elif s['status'] == 'rejected':
                col1, col2 = st.columns(2)
                with col1:
                    st.error("✗ Rejected")
                with col2:
                    if st.button("↺ Reset", key=f"reset_{s['line_number']}", use_container_width=True):
                        s['status'] = 'pending'
                        st.rerun()
    
    st.markdown("---")
    
    approved = [s for s in suggestions if s['status'] == 'accepted']
    if st.button(f"🔧 Apply {len(approved)} Changes", 
                 use_container_width=True, 
                 type="primary",
                 disabled=(len(approved) == 0)):
        with st.spinner("Applying changes by line number..."):
            final = apply_changes_by_line(
                st.session_state.latex_content,
                approved
            )
            
            if final:
                # Clean up the LaTeX - remove any text before \documentclass
                import re
                match = re.search(r'\\documentclass', final)
                if match:
                    final = final[match.start():]
                
                st.session_state.final_latex = final
                st.session_state.step = 4
                st.rerun()

# STEP 4: Final
elif st.session_state.step == 4:
    st.success("🎉 Optimized Resume Ready!")
    
    # Show LaTeX content
    st.text_area("Final LaTeX", st.session_state.final_latex, height=400)
    
    st.markdown("---")
    
    # Download options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.download_button(
            "📥 Download LaTeX",
            st.session_state.final_latex,
            "optimized_resume.tex",
            use_container_width=True,
            type="secondary"
        )
    
    with col2:
        if st.button("📄 Generate PDF", use_container_width=True, type="primary"):
            with st.spinner("Compiling PDF..."):
                pdf_data = compile_latex_to_pdf(st.session_state.final_latex)
                if pdf_data:
                    st.session_state.pdf_data = pdf_data
                    st.rerun()
    
    with col3:
        if st.button("🔄 New Optimization", use_container_width=True):
            st.session_state.step = 1
            st.session_state.suggestions = []
            st.session_state.job_analysis = None
            st.session_state.final_latex = None
            st.session_state.pdf_data = None
            st.rerun()
    
    # Show PDF download if generated
    if 'pdf_data' in st.session_state and st.session_state.pdf_data:
        st.success("✅ PDF Generated Successfully!")
        st.download_button(
            "📥 Download PDF",
            get_pdf_download_data(st.session_state.pdf_data),
            "optimized_resume.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# Sidebar Log
with st.sidebar:
    st.header("🤖 Agent Log")
    if st.session_state.log:
        for entry in st.session_state.log[-10:]:
            icon = {'success': '✅', 'error': '❌', 'info': 'ℹ️', 'warning': '⚠️'}.get(entry['type'], 'ℹ️')
            st.caption(f"{icon} `[{entry['time']}]` {entry['message']}")
    else:
        st.caption("No activity yet...")
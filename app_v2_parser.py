"""
Agentic Resume Optimizer V2 - With Robust LaTeX Parser
Uses structured parsing to eliminate text matching issues
"""

import streamlit as st
import json
from groq import Groq
from datetime import datetime
import os
from dotenv import load_dotenv
from latex_parser import LaTeXResumeParser
import subprocess
import re

# Load environment variables
load_dotenv()

# Session state
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'job_analysis' not in st.session_state:
    st.session_state.job_analysis = None
if 'suggestions' not in st.session_state:
    st.session_state.suggestions = []
if 'final_latex' not in st.session_state:
    st.session_state.final_latex = None
if 'log' not in st.session_state:
    st.session_state.log = []
if 'api_key' not in st.session_state:
    st.session_state.api_key = os.getenv('GROQ_API_KEY', '')
if 'parser' not in st.session_state:
    st.session_state.parser = None
if 'resume_tree' not in st.session_state:
    st.session_state.resume_tree = None

def add_log(message, level='info'):
    """Add timestamped log entry"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    emoji = {'info': 'ℹ️', 'success': '✅', 'error': '❌', 'warning': '⚠️'}
    st.session_state.log.append(f"{emoji.get(level, 'ℹ️')} [{timestamp}] {message}")

def escape_latex(text):
    """Escape special LaTeX characters"""
    replacements = {
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '&': r'\&',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}'
    }
    for char, escaped in replacements.items():
        text = text.replace(char, escaped)
    return text

def compile_latex_to_pdf(latex_content, output_filename="resume"):
    """Compile LaTeX to PDF"""
    import tempfile
    import shutil
    
    try:
        add_log('🔨 Compiling LaTeX to PDF...', 'info')
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, f"{output_filename}.tex")
            
            # Clean LaTeX content
            latex_content = re.sub(r'^.*?\\documentclass', r'\\documentclass', latex_content, flags=re.DOTALL)
            latex_content = re.sub(r'```latex\n?', '', latex_content)
            latex_content = re.sub(r'```\n?', '', latex_content)
            
            with open(tex_file, 'w') as f:
                f.write(latex_content)
            
            # Add MacTeX to PATH
            env = os.environ.copy()
            env['PATH'] = '/Library/TeX/texbin:' + env.get('PATH', '')
            
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', f"{output_filename}.tex"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                env=env
            )
            
            pdf_file = os.path.join(tmpdir, f"{output_filename}.pdf")
            
            if os.path.exists(pdf_file):
                with open(pdf_file, 'rb') as f:
                    pdf_data = f.read()
                add_log('✅ PDF compiled successfully!', 'success')
                return pdf_data
            else:
                error_msg = result.stderr if result.stderr else "PDF file not generated"
                add_log(f'❌ PDF compilation failed: {error_msg}', 'error')
                return None
                
    except FileNotFoundError:
        add_log('❌ pdflatex not found. Please install MacTeX.', 'error')
        return None
    except Exception as e:
        add_log(f'❌ PDF compilation error: {str(e)}', 'error')
        return None

def analyze_job(api_key, job_description):
    """Step 1: Analyze job description"""
    add_log('🔍 Analyzing job requirements...', 'info')
    
    # Validate API key
    if not api_key:
        st.error("⚠️ Please enter your Groq API key in the sidebar.")
        return None
    
    # Validate input is not LaTeX
    if '\\documentclass' in job_description or '\\begin{document}' in job_description:
        add_log('❌ Please paste a JOB DESCRIPTION, not a resume!', 'error')
        st.error("⚠️ You pasted a LaTeX resume. Please paste the JOB DESCRIPTION you want to optimize for.")
        return None
    
    # Validate job description is not empty
    if not job_description or len(job_description.strip()) < 50:
        st.error("⚠️ Please enter a more detailed job description (at least 50 characters).")
        return None
    
    try:
        client = Groq(api_key=api_key)
        
        add_log(f'Sending {len(job_description)} chars to AI...', 'info')
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "system",
                "content": "You are a job description analyzer. Extract key requirements and return ONLY valid JSON, nothing else."
            }, {
                "role": "user",
                "content": f"""Extract key requirements from this job description and return as JSON:

{job_description}

Return ONLY this JSON structure (no other text):
{{
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1", "skill2"],
  "technologies": ["tech1", "tech2"],
  "keywords": ["keyword1", "keyword2"]
}}"""
            }],
            temperature=0.3,
            max_tokens=1500
        )
        
        content = response.choices[0].message.content.strip()
        add_log(f'Received {len(content)} chars from AI', 'info')
        
        # Clean markdown code blocks and other formatting
        content = re.sub(r'^```json\n?', '', content)
        content = re.sub(r'^```\n?', '', content)
        content = re.sub(r'\n?```$', '', content)
        content = content.strip()
        
        # If content is empty or doesn't look like JSON, show error
        if not content or (not content.startswith('{') and not content.startswith('[')):
            add_log(f'❌ AI returned invalid response', 'error')
            st.error("AI didn't return valid JSON. Please try again.")
            with st.expander("Debug: Raw AI Response"):
                st.text(content if content else "Empty response")
            return None
        
        # Try to parse JSON
        try:
            analysis = json.loads(content)
            
            # Validate structure
            if not isinstance(analysis, dict):
                st.error("Invalid response structure. Please try again.")
                return None
            
            # Ensure required fields exist
            if 'required_skills' not in analysis:
                analysis['required_skills'] = []
            if 'preferred_skills' not in analysis:
                analysis['preferred_skills'] = []
            if 'technologies' not in analysis:
                analysis['technologies'] = []
            if 'keywords' not in analysis:
                analysis['keywords'] = []
            
            add_log('✓ Job analysis complete', 'success')
            return analysis
            
        except json.JSONDecodeError as je:
            add_log(f'❌ JSON parsing error: {str(je)}', 'error')
            st.error(f"Failed to parse AI response. Error: {str(je)}")
            with st.expander("Debug: Raw AI Response"):
                st.code(content, language="text")
            return None
    
    except Exception as e:
        add_log(f'❌ Analysis failed: {str(e)}', 'error')
        st.error(f"Error communicating with AI: {str(e)}")
        if "api_key" in str(e).lower():
            st.error("⚠️ API key issue. Please check your Groq API key in the sidebar.")
        return None

def generate_suggestions(api_key, job_analysis, parser, resume_tree, cv_context):
    """Step 2: Generate suggestions using parsed resume structure"""
    add_log('🤖 Agent analyzing keyword gaps using structured resume...', 'info')
    
    try:
        client = Groq(api_key=api_key)
        
        # Get displayable tree for AI
        tree_display = parser.get_displayable_tree()
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "system",
                "content": "You are a strategic resume optimizer. Return ONLY valid JSON, no other text before or after."
            }, {
                "role": "user",
                "content": f"""Analyze this resume structure and suggest keyword improvements.

JOB REQUIREMENTS:
{json.dumps(job_analysis, indent=2)}

STRUCTURED RESUME (with element IDs in brackets):
{tree_display}

CANDIDATE'S BACKGROUND:
{cv_context or 'No additional context'}

CRITICAL INSTRUCTIONS:
1. Extract the ID from brackets (e.g., [abc123def456] → use "abc123def456")
2. Return ONLY the JSON array, no explanatory text
3. Suggest 3-5 high-impact changes maximum

Return ONLY this JSON structure (nothing else):
[
  {{
    "element_id": "abc123def456",
    "action": "modify",
    "suggested_text": "Plain text without LaTeX commands",
    "reasoning": "Missing keywords: X, Y, Z",
    "impact": "high",
    "keywords_added": ["keyword1", "keyword2"]
  }}
]

Valid actions:
- "modify": Change existing bullet/skill text (use element_id of the bullet)
- "remove": Delete bullet/skill (use element_id of the bullet)
- "add_to": Add new bullet to company/project (use element_id of parent company/project)

For Skills section modifications:
- To modify a skill category (e.g., Programming, Databases), use that category's element_id
- The suggested_text should be the COMPLETE new list of skills for that category"""
            }],
            temperature=0.5,
            max_tokens=4000
        )
        
        content = response.choices[0].message.content.strip()
        
        # Clean markdown code blocks
        content = re.sub(r'^```json\n?', '', content)
        content = re.sub(r'^```\n?', '', content)
        content = re.sub(r'\n?```$', '', content)
        content = content.strip()
        
        # Try to extract JSON array if there's extra text
        # Look for the first [ and last ]
        if not content.startswith('['):
            start_idx = content.find('[')
            if start_idx > 0:
                add_log(f'⚠️ Removing {start_idx} chars of extra text before JSON', 'warning')
                content = content[start_idx:]
        
        if not content.endswith(']'):
            end_idx = content.rfind(']')
            if end_idx > 0:
                add_log(f'⚠️ Removing extra text after JSON', 'warning')
                content = content[:end_idx + 1]
        
        # Try to parse JSON
        try:
            suggestions = json.loads(content)
            
            # Validate it's a list
            if not isinstance(suggestions, list):
                st.error("AI didn't return a list of suggestions. Please try again.")
                return None
            
            # Clean element_ids (remove brackets if present)
            for s in suggestions:
                if 'element_id' in s and isinstance(s['element_id'], str):
                    # Remove brackets like [abc123] -> abc123
                    s['element_id'] = s['element_id'].strip('[]')
            
            add_log(f'✅ Generated {len(suggestions)} strategic suggestions', 'success')
            return suggestions
            
        except json.JSONDecodeError as je:
            add_log(f'❌ JSON parsing error: {str(je)}', 'error')
            st.error(f"Failed to parse suggestions. Error: {str(je)}")
            with st.expander("Debug: Raw AI Response"):
                st.code(content, language="text")
            return None
            with st.expander("Debug: Raw AI Response"):
                st.code(content)
            return None
    
    except Exception as e:
        add_log(f'❌ Failed: {str(e)}', 'error')
        st.error(f"Error: {str(e)}")
        return None

def apply_changes_by_id(parser, approved_suggestions):
    """Step 3: Apply changes using element IDs (robust, no text matching!)"""
    add_log(f'🔧 Applying {len(approved_suggestions)} changes by ID...', 'info')
    
    try:
        modified_resume = parser.latex_content
        changes_made = []
        
        for suggestion in approved_suggestions:
            element_id = suggestion['element_id']
            action = suggestion['action']
            suggested_text = escape_latex(suggestion['suggested_text']) if suggestion.get('suggested_text') else ""
            
            try:
                if action == 'add_to':
                    # Add new bullet to parent element
                    modified_resume = add_bullet_to_element(modified_resume, element_id, suggested_text, parser)
                    changes_made.append(f"Added bullet to {element_id}")
                    add_log(f"✓ Added bullet to element {element_id}", 'success')
                
                elif action == 'modify':
                    # Modify element by ID
                    modified_resume = parser.apply_edit_by_id(element_id, 'modify', suggested_text)
                    changes_made.append(f"Modified {element_id}")
                    add_log(f"✓ Modified element {element_id}", 'success')
                
                elif action == 'remove':
                    # Remove element by ID
                    modified_resume = parser.apply_edit_by_id(element_id, 'remove')
                    changes_made.append(f"Removed {element_id}")
                    add_log(f"✓ Removed element {element_id}", 'success')
                
                # Update parser with new content for next iteration
                parser.latex_content = modified_resume
                
            except ValueError as ve:
                add_log(f"⚠️ Could not find element {element_id}: {str(ve)}", 'warning')
                continue
        
        add_log(f'✅ Applied {len(changes_made)} changes successfully!', 'success')
        return modified_resume
    
    except Exception as e:
        add_log(f'❌ Failed: {str(e)}', 'error')
        st.error(f"Error: {str(e)}")
        return None

def add_bullet_to_element(latex_content, parent_id, bullet_text, parser):
    """Add a new bullet to a parent element (company/project)"""
    if parent_id not in parser.id_to_position:
        raise ValueError(f"Parent element not found: {parent_id}")
    
    start_pos, end_pos = parser.id_to_position[parent_id]
    parent_content = latex_content[start_pos:end_pos]
    
    # Find \resumeItemListEnd in parent
    list_end_pos = parent_content.find(r'\resumeItemListEnd')
    if list_end_pos < 0:
        raise ValueError(f"No bullet list found in parent {parent_id}")
    
    # Insert new bullet before \resumeItemListEnd
    new_bullet = f"\n        \\resumeItem{{{bullet_text}}}"
    absolute_insert_pos = start_pos + list_end_pos
    
    modified = latex_content[:absolute_insert_pos] + new_bullet + "\n      " + latex_content[absolute_insert_pos:]
    return modified

# ==================
# UI
# ==================

st.title("🤖 Agentic Resume Optimizer V2")
st.markdown("**NEW:** Uses robust LaTeX parser - zero text matching errors!")

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

st.divider()

# API Key
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key_input = st.text_input("Groq API Key", value=st.session_state.api_key, type="password")
    if api_key_input:
        st.session_state.api_key = api_key_input
    
    if st.button("🔄 Reset Workflow"):
        st.session_state.step = 1
        st.session_state.job_analysis = None
        st.session_state.suggestions = []
        st.session_state.final_latex = None
        st.session_state.parser = None
        st.session_state.resume_tree = None
        st.rerun()

# Step 1: Upload
if st.session_state.step == 1:
    st.header("📄 Step 1: Upload Resume")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Your Resume")
        latex_file = st.file_uploader("Upload LaTeX Resume (.tex)", type=['tex'])
        cv_context_file = st.file_uploader("(Optional) Upload CV Context (.txt)", type=['txt'])
    
    with col2:
        st.subheader("💼 Target Job")
        st.info("⚠️ Paste the JOB DESCRIPTION here, not your resume!")
        job_desc = st.text_area("Paste Job Description", height=200, 
                                placeholder="Example:\n\nWe are seeking a Senior Software Engineer...\n\nRequired Skills:\n- Python, Java\n- AWS, Docker\n- 5+ years experience")
    
    if st.button("🚀 Start Analysis") and latex_file and job_desc:
        # Validate job description is not LaTeX
        if '\\documentclass' in job_desc or '\\begin{document}' in job_desc:
            st.error("⚠️ You pasted a LaTeX resume in the Job Description field! Please paste the actual job description you're applying to.")
        else:
            with st.spinner("Parsing resume structure..."):
                latex_content = latex_file.read().decode('utf-8')
                cv_context = cv_context_file.read().decode('utf-8') if cv_context_file else None
                
                # Parse LaTeX into structured tree
                parser = LaTeXResumeParser(latex_content)
                tree = parser.parse()
                
                st.session_state.parser = parser
                st.session_state.resume_tree = tree
                st.session_state.latex_resume = latex_content
                st.session_state.cv_context = cv_context
                st.session_state.job_desc = job_desc
                
                add_log(f"✅ Parsed resume: {len(tree['sections'])} sections", 'success')
                
                # Show parsed structure
                st.success("Resume parsed successfully!")
                with st.expander("View Parsed Structure"):
                    st.code(parser.get_displayable_tree(), language="text")
                
                # Analyze job
                analysis = analyze_job(st.session_state.api_key, job_desc)
                if analysis:
                    st.session_state.job_analysis = analysis
                    st.session_state.step = 2
                    st.rerun()

# Step 2: Generate Suggestions
elif st.session_state.step == 2:
    st.header("🤖 Step 2: AI Analysis")
    
    st.json(st.session_state.job_analysis)
    
    if st.button("Generate Suggestions"):
        with st.spinner("Analyzing keyword gaps..."):
            suggestions = generate_suggestions(
                st.session_state.api_key,
                st.session_state.job_analysis,
                st.session_state.parser,
                st.session_state.resume_tree,
                st.session_state.get('cv_context')
            )
            
            if suggestions:
                # Add status and modified_text fields
                for s in suggestions:
                    s['status'] = 'pending'
                    s['modified_text'] = s.get('suggested_text', '')
                
                st.session_state.suggestions = suggestions
                st.session_state.step = 3
                st.rerun()

# Step 3: Review Suggestions
elif st.session_state.step == 3:
    st.header("📝 Step 3: Review & Edit Suggestions")
    
    for i, s in enumerate(st.session_state.suggestions):
        with st.expander(f"{'✅' if s['status'] == 'accepted' else '⏸️' if s['status'] == 'pending' else '❌'} Suggestion {i+1}: {s['action']} [{s['element_id'][:8]}...]", expanded=(s['status'] == 'pending')):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Action:** {s['action']}")
                st.write(f"**Element ID:** `{s['element_id']}`")
                st.write(f"**Impact:** {s['impact']}")
                st.write(f"**Reasoning:** {s['reasoning']}")
                
                if s.get('keywords_added'):
                    st.info(f"🔑 Keywords: {', '.join(s['keywords_added'])}")
                
                st.text_area(f"Suggested Text {i}", value=s['modified_text'], key=f"text_{i}", height=100)
            
            with col2:
                if st.button("✅ Accept", key=f"accept_{i}"):
                    s['status'] = 'accepted'
                    s['modified_text'] = st.session_state[f"text_{i}"]
                    st.rerun()
                
                if st.button("❌ Reject", key=f"reject_{i}"):
                    s['status'] = 'rejected'
                    st.rerun()
    
    st.divider()
    
    approved = [s for s in st.session_state.suggestions if s['status'] == 'accepted']
    st.write(f"**Approved:** {len(approved)} | **Pending:** {len([s for s in st.session_state.suggestions if s['status'] == 'pending'])} | **Rejected:** {len([s for s in st.session_state.suggestions if s['status'] == 'rejected'])}")
    
    if st.button("🔨 Apply Changes", disabled=len(approved) == 0):
        with st.spinner("Applying changes by ID..."):
            # Convert to format expected by apply function
            approved_formatted = []
            for s in approved:
                approved_formatted.append({
                    'element_id': s['element_id'],
                    'action': s['action'],
                    'suggested_text': s['modified_text']
                })
            
            final = apply_changes_by_id(st.session_state.parser, approved_formatted)
            if final:
                st.session_state.final_latex = final
                st.session_state.step = 4
                st.rerun()

# Step 4: Final Resume
elif st.session_state.step == 4:
    st.header("🎉 Step 4: Final Resume")
    
    st.download_button("📥 Download LaTeX", st.session_state.final_latex, "optimized_resume.tex")
    
    if st.button("📄 Generate PDF"):
        with st.spinner("Compiling PDF..."):
            pdf_data = compile_latex_to_pdf(st.session_state.final_latex)
            if pdf_data:
                st.download_button("📥 Download PDF", pdf_data, "optimized_resume.pdf", mime="application/pdf")
    
    with st.expander("View LaTeX"):
        st.code(st.session_state.final_latex, language="latex")

# Logs (Always visible at bottom)
st.divider()
st.subheader("📋 Activity Log")
if st.session_state.log:
    log_container = st.container()
    with log_container:
        for log in st.session_state.log[-10:]:  # Show last 10 logs
            st.text(log)
    
    if len(st.session_state.log) > 10:
        with st.expander(f"View All {len(st.session_state.log)} Logs"):
            for log in st.session_state.log:
                st.text(log)
else:
    st.info("No activity yet. Start by uploading your resume!")

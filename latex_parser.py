"""
Robust LaTeX Resume Parser
Converts LaTeX resume into a structured tree with unique IDs for each element.
This eliminates text matching issues by allowing edits via ID references.
"""

import re
from typing import Dict, List, Any
import hashlib

class LaTeXResumeParser:
    """Parse LaTeX resume into a structured tree with unique IDs"""
    
    def __init__(self, latex_content: str):
        self.latex_content = latex_content
        self.tree = {
            "sections": [],
            "preamble": "",
            "document_class": "",
            "metadata": {}
        }
        self.id_to_position = {}  # Maps IDs to (start_pos, end_pos) in original text
        
    def parse(self) -> Dict[str, Any]:
        """Main parsing function - returns structured tree"""
        # Extract document structure
        self._extract_preamble()
        self._extract_sections()
        return self.tree
    
    def _extract_preamble(self):
        """Extract document class and preamble"""
        doc_class_match = re.search(r'\\documentclass\{[^}]+\}', self.latex_content)
        if doc_class_match:
            self.tree['document_class'] = doc_class_match.group(0)
        
        # Everything before \begin{document}
        begin_doc = self.latex_content.find(r'\begin{document}')
        if begin_doc > 0:
            self.tree['preamble'] = self.latex_content[:begin_doc]
    
    def _extract_sections(self):
        """Extract all sections (Work Experience, Projects, Skills, etc.)"""
        # Find all \section{...} commands
        section_pattern = r'\\section\{([^}]+)\}'
        section_matches = list(re.finditer(section_pattern, self.latex_content))
        
        for i, match in enumerate(section_matches):
            section_name = match.group(1)
            section_start = match.start()
            
            # Find section end (next section or end of document)
            if i + 1 < len(section_matches):
                section_end = section_matches[i + 1].start()
            else:
                # Last section - find \end{document}
                end_doc = self.latex_content.find(r'\end{document}')
                section_end = end_doc if end_doc > 0 else len(self.latex_content)
            
            section_content = self.latex_content[section_start:section_end]
            
            # Parse based on section type
            if section_name in ['Work Experience', 'Experience', 'Professional Experience']:
                parsed_section = self._parse_experience_section(section_content, section_start, section_name)
            elif section_name in ['Projects', 'Personal Projects']:
                parsed_section = self._parse_projects_section(section_content, section_start, section_name)
            elif section_name == 'Skills':
                parsed_section = self._parse_skills_section(section_content, section_start, section_name)
            elif section_name == 'Education':
                parsed_section = self._parse_education_section(section_content, section_start, section_name)
            else:
                # Generic section
                parsed_section = self._parse_generic_section(section_content, section_start, section_name)
            
            self.tree['sections'].append(parsed_section)
    
    def _parse_experience_section(self, content: str, start_pos: int, section_name: str) -> Dict:
        """Parse Work Experience section"""
        section_id = self._generate_id(f"section_{section_name}")
        
        section_data = {
            "id": section_id,
            "type": "experience",
            "name": section_name,
            "items": []
        }
        
        # Find all \resumeSubheading entries (company/title/dates)
        subheading_pattern = r'\\resumeSubheading\s*\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}'
        subheading_matches = list(re.finditer(subheading_pattern, content))
        
        for i, match in enumerate(subheading_matches):
            title = match.group(1).strip()
            company = match.group(2).strip()
            dates = match.group(3).strip()
            location = match.group(4).strip()
            
            item_start = start_pos + match.start()
            
            # Find bullets for this experience
            # Look for \resumeItemListStart ... \resumeItemListEnd
            list_start_pos = content.find(r'\resumeItemListStart', match.end())
            list_end_pos = content.find(r'\resumeItemListEnd', match.end())
            
            bullets = []
            if list_start_pos > 0 and list_end_pos > list_start_pos:
                bullets_content = content[list_start_pos:list_end_pos]
                bullets = self._parse_resume_items(bullets_content, start_pos + list_start_pos)
            
            item_id = self._generate_id(f"{company}_{title}")
            item_end = start_pos + (list_end_pos if list_end_pos > 0 else match.end())
            
            self.id_to_position[item_id] = (item_start, item_end)
            
            section_data['items'].append({
                "id": item_id,
                "title": title,
                "company": company,
                "dates": dates,
                "location": location,
                "bullets": bullets
            })
        
        return section_data
    
    def _parse_projects_section(self, content: str, start_pos: int, section_name: str) -> Dict:
        """Parse Projects section (similar to experience)"""
        section_id = self._generate_id(f"section_{section_name}")
        
        section_data = {
            "id": section_id,
            "type": "projects",
            "name": section_name,
            "items": []
        }
        
        # Projects use \resumeProjectHeading
        project_pattern = r'\\resumeProjectHeading\s*\{\\textbf\{([^}]+)\}[^}]*\}\{([^}]+)\}'
        project_matches = list(re.finditer(project_pattern, content))
        
        for match in project_matches:
            project_name = match.group(1).strip()
            project_tech = match.group(2).strip()
            
            item_start = start_pos + match.start()
            
            # Find bullets
            list_start_pos = content.find(r'\resumeItemListStart', match.end())
            list_end_pos = content.find(r'\resumeItemListEnd', match.end())
            
            bullets = []
            if list_start_pos > 0 and list_end_pos > list_start_pos:
                bullets_content = content[list_start_pos:list_end_pos]
                bullets = self._parse_resume_items(bullets_content, start_pos + list_start_pos)
            
            item_id = self._generate_id(f"project_{project_name}")
            item_end = start_pos + (list_end_pos if list_end_pos > 0 else match.end())
            
            self.id_to_position[item_id] = (item_start, item_end)
            
            section_data['items'].append({
                "id": item_id,
                "name": project_name,
                "technologies": project_tech,
                "bullets": bullets
            })
        
        return section_data
    
    def _parse_skills_section(self, content: str, start_pos: int, section_name: str) -> Dict:
        """Parse Skills section"""
        section_id = self._generate_id(f"section_{section_name}")
        
        section_data = {
            "id": section_id,
            "type": "skills",
            "name": section_name,
            "categories": []
        }
        
        # Skills use: \textbf{Category}{: items}
        skills_pattern = r'\\textbf\{([^}]+)\}\{:\s*([^}]+)\}'
        skills_matches = list(re.finditer(skills_pattern, content))
        
        for match in skills_matches:
            category = match.group(1).strip()
            items = match.group(2).strip()
            
            cat_id = self._generate_id(f"skill_{category}")
            cat_start = start_pos + match.start()
            cat_end = start_pos + match.end()
            
            self.id_to_position[cat_id] = (cat_start, cat_end)
            
            section_data['categories'].append({
                "id": cat_id,
                "category": category,
                "items": items
            })
        
        return section_data
    
    def _parse_education_section(self, content: str, start_pos: int, section_name: str) -> Dict:
        """Parse Education section"""
        section_id = self._generate_id(f"section_{section_name}")
        
        section_data = {
            "id": section_id,
            "type": "education",
            "name": section_name,
            "items": []
        }
        
        # Education uses \resumeSubheading
        edu_pattern = r'\\resumeSubheading\s*\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}'
        edu_matches = list(re.finditer(edu_pattern, content))
        
        for match in edu_matches:
            degree = match.group(1).strip()
            school = match.group(2).strip()
            dates = match.group(3).strip()
            location = match.group(4).strip()
            
            item_id = self._generate_id(f"edu_{school}")
            item_start = start_pos + match.start()
            item_end = start_pos + match.end()
            
            self.id_to_position[item_id] = (item_start, item_end)
            
            section_data['items'].append({
                "id": item_id,
                "degree": degree,
                "school": school,
                "dates": dates,
                "location": location
            })
        
        return section_data
    
    def _parse_generic_section(self, content: str, start_pos: int, section_name: str) -> Dict:
        """Parse any other section"""
        section_id = self._generate_id(f"section_{section_name}")
        
        return {
            "id": section_id,
            "type": "generic",
            "name": section_name,
            "content": content
        }
    
    def _parse_resume_items(self, content: str, start_pos: int) -> List[Dict]:
        """Parse \resumeItem{...} bullets"""
        bullets = []
        
        # Match \resumeItem{...} including nested braces
        item_pattern = r'\\resumeItem\{((?:[^{}]|\{[^{}]*\})*)\}'
        item_matches = list(re.finditer(item_pattern, content))
        
        for match in item_matches:
            bullet_text = match.group(1).strip()
            bullet_id = self._generate_id(f"bullet_{bullet_text[:30]}")
            bullet_start = start_pos + match.start()
            bullet_end = start_pos + match.end()
            
            self.id_to_position[bullet_id] = (bullet_start, bullet_end)
            
            bullets.append({
                "id": bullet_id,
                "text": bullet_text
            })
        
        return bullets
    
    def _generate_id(self, text: str) -> str:
        """Generate unique ID from text"""
        # Use hash to create short unique ID
        hash_obj = hashlib.md5(text.encode())
        return hash_obj.hexdigest()[:12]
    
    def get_displayable_tree(self) -> str:
        """Convert tree to readable format for AI"""
        lines = []
        lines.append("=== RESUME STRUCTURE ===\n")
        
        for section in self.tree['sections']:
            lines.append(f"\n📁 [{section['id']}] {section['name']} ({section['type']})")
            
            if section['type'] == 'skills':
                for cat in section['categories']:
                    lines.append(f"  └─ [{cat['id']}] {cat['category']}: {cat['items']}")
            
            elif section['type'] in ['experience', 'projects']:
                for item in section['items']:
                    if section['type'] == 'experience':
                        lines.append(f"  └─ [{item['id']}] {item['title']} at {item['company']}")
                    else:
                        lines.append(f"  └─ [{item['id']}] {item['name']}")
                    
                    for bullet in item['bullets']:
                        preview = bullet['text'][:80] + "..." if len(bullet['text']) > 80 else bullet['text']
                        lines.append(f"      • [{bullet['id']}] {preview}")
            
            elif section['type'] == 'education':
                for item in section['items']:
                    lines.append(f"  └─ [{item['id']}] {item['degree']} - {item['school']}")
        
        return "\n".join(lines)
    
    def apply_edit_by_id(self, element_id: str, action: str, new_text: str = None) -> str:
        """
        Apply edit to element by ID
        
        Args:
            element_id: Unique ID of element to edit
            action: 'modify', 'remove', or 'add'
            new_text: New text content (for modify/add)
        
        Returns:
            Modified LaTeX content
        """
        if element_id not in self.id_to_position:
            raise ValueError(f"Element ID not found: {element_id}")
        
        start_pos, end_pos = self.id_to_position[element_id]
        modified_content = self.latex_content
        
        if action == 'remove':
            # Remove element
            modified_content = modified_content[:start_pos] + modified_content[end_pos:]
        
        elif action == 'modify':
            # Replace element content
            old_element = modified_content[start_pos:end_pos]
            
            # Detect element type and reconstruct
            if r'\resumeItem{' in old_element:
                new_element = f"\\resumeItem{{{new_text}}}"
            elif r'\textbf{' in old_element:
                # Skills category - extract category name
                category_match = re.search(r'\\textbf\{([^}]+)\}', old_element)
                if category_match:
                    category = category_match.group(1)
                    new_element = f"\\textbf{{{category}}}{{: {new_text}}}"
                else:
                    new_element = new_text
            else:
                new_element = new_text
            
            modified_content = modified_content[:start_pos] + new_element + modified_content[end_pos:]
        
        return modified_content


def test_parser():
    """Test the parser with sample LaTeX"""
    sample = r"""
\documentclass{article}
\begin{document}

\section{Work Experience}
\resumeSubheading{Data Engineer}{TekLink International}{Jan 2024}{Remote}
\resumeItemListStart
    \resumeItem{Built data pipelines}
    \resumeItem{Deployed ML models}
\resumeItemListEnd

\section{Skills}
\textbf{Programming}{: Python, JavaScript, Java}
\textbf{Cloud}{: AWS, GCP, Azure}

\end{document}
"""
    
    parser = LaTeXResumeParser(sample)
    tree = parser.parse()
    print(parser.get_displayable_tree())
    print("\n\nTree structure:")
    print(tree)


if __name__ == "__main__":
    test_parser()

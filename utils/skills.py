import os
import re
import json
from pathlib import Path
from utils.cfg_man import cfg, deep_update

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """
    Parses YAML frontmatter from a markdown file.
    Returns a tuple of (frontmatter_dict, markdown_body).
    """
    lines = content.split('\n')
    if not lines or lines[0].strip() != '---':
        return {}, content

    frontmatter = {}
    body_start_idx = 1
    
    for i in range(1, len(lines)):
        line = lines[i].strip()
        if line == '---':
            body_start_idx = i + 1
            break
        
        # Simple key: value parsing
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            frontmatter[key] = value

    body = '\n'.join(lines[body_start_idx:])
    return frontmatter, body

class SkillManager:
    def __init__(self):
        self.skills = {}
        self.discover_skills()

    def discover_skills(self):
        """
        Scans for SKILL.md files in directories specified in config (skills.directories).
        Later directories in the list override skills from earlier directories.
        """
        self.skills = {}
        working_dir = cfg.get('session.working_directory', os.getcwd())
        
        default_dirs = [
            "$CODY_DIR/skills",
            "~/.agents/skills",
            "{working_directory}/.agents/skills"
        ]
        
        directories = cfg.get('skills.directories', default_dirs)
        if isinstance(directories, str):
            try:
                import ast
                directories = ast.literal_eval(directories)
            except Exception:
                directories = [directories]
        if not isinstance(directories, list):
            directories = default_dirs
            
        from utils.paths import resolve_dir_templates
        search_paths = [Path(d) for d in resolve_dir_templates(directories, working_dir)]
        
        for base_path in search_paths:
            if not base_path.exists() or not base_path.is_dir():
                continue
                
            # Scan subdirectories for SKILL.md
            for skill_dir in base_path.iterdir():
                if not skill_dir.is_dir():
                    continue
                    
                skill_file = skill_dir / 'SKILL.md'
                if not skill_file.exists():
                    continue
                    
                try:
                    with open(skill_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    frontmatter, body = parse_frontmatter(content)
                    
                    name = frontmatter.get('name')
                    description = frontmatter.get('description')
                    
                    if not name or not description:
                        # Skip if missing required fields
                        continue
                        
                    # Check if skill is explicitly disabled in config
                    enabled_config = cfg.get('skills.enabled', {})
                    if isinstance(enabled_config, dict) and name in enabled_config:
                        if not enabled_config[name]:
                            continue
                            
                    skill_config_path = skill_dir / 'config.json'
                    if skill_config_path.exists():
                        try:
                            with open(skill_config_path, 'r', encoding='utf-8') as f:
                                skill_defaults = json.load(f)
                            existing = cfg.data.get(name, {})
                            cfg.data[name] = deep_update(skill_defaults, existing)
                        except Exception as e:
                            print(f"Error loading skill config {skill_config_path}: {e}")
                
                    self.skills[name] = {
                        'name': name,
                        'description': description,
                        'location': str(skill_file),
                        'base_dir': str(skill_dir),
                        'body': body
                    }

                except Exception as e:
                    print(f"Error loading skill {skill_file}: {e}")

    def get_catalog_xml(self) -> str:
        """
        Returns an XML representation of available skills for the agent prompt.
        Always re-discovers skills to ensure hot-loaded config changes are respected.
        """
        self.discover_skills()
        
        if not self.skills:
            return ""
            
        xml = "<available_skills>\n"
        for name, skill in self.skills.items():
            xml += "  <skill>\n"
            xml += f"    <name>{skill['name']}</name>\n"
            xml += f"    <description>{skill['description']}</description>\n"
            xml += f"    <location>{skill['location']}</location>\n"
            xml += "  </skill>\n"
        xml += "</available_skills>\n"
        
        return xml

    def get_skill(self, name: str) -> dict | None:
        self.discover_skills()
        return self.skills.get(name)

skill_manager = SkillManager()

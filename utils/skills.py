import os
import re
from pathlib import Path
from utils.cfg_man import cfg, register_default_config
from utils.paths import parse_directory_list, resolve_dir_templates, tiered_dir_templates

register_default_config({
  "skills": {
    "directories": tiered_dir_templates("skills"),
    "enabled": {},
  },
})

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


def skill_command_directory_paths(working_dir: str) -> list[str]:
    """
    Absolute paths to existing skill `cmd/` dirs, in load order (later overrides).
    Mirrors SkillManager.discover_skills tier roots and per-skill folder rules:
    only directories with SKILL.md, valid name/description frontmatter, and not
    disabled via skills.enabled; skill folders sorted by name per tier.
    """
    default_dirs = tiered_dir_templates("skills")
    directories = parse_directory_list(
        cfg.get('skills.directories', default_dirs),
        default_dirs,
    )
    search_paths = [Path(d) for d in resolve_dir_templates(directories, working_dir)]
    out: list[str] = []

    for base_path in search_paths:
        if not base_path.exists() or not base_path.is_dir():
            continue
        skill_dirs = sorted(
            (p for p in base_path.iterdir() if p.is_dir()),
            key=lambda p: p.name.lower(),
        )
        for skill_dir in skill_dirs:
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                with open(skill_file, encoding="utf-8") as f:
                    content = f.read()
                frontmatter, _ = parse_frontmatter(content)
                name = frontmatter.get("name")
                description = frontmatter.get("description")
                if not name or not description:
                    continue
                enabled_config = cfg.get("skills.enabled", {})
                if isinstance(enabled_config, dict) and name in enabled_config:
                    if not enabled_config[name]:
                        continue
            except OSError:
                continue
            cmd_dir = skill_dir / "cmd"
            if cmd_dir.is_dir():
                out.append(str(cmd_dir.resolve()))

    return out


def skill_tools_directory_paths(working_dir: str) -> list[str]:
    """
    Absolute paths to existing skill `tools/` dirs (roots for fs.load_folder), in load order.
    Same tier / SKILL.md / skills.enabled rules as skill_command_directory_paths.
    """
    default_dirs = tiered_dir_templates("skills")
    directories = parse_directory_list(
        cfg.get('skills.directories', default_dirs),
        default_dirs,
    )
    search_paths = [Path(d) for d in resolve_dir_templates(directories, working_dir)]
    out: list[str] = []

    for base_path in search_paths:
        if not base_path.exists() or not base_path.is_dir():
            continue
        skill_dirs = sorted(
            (p for p in base_path.iterdir() if p.is_dir()),
            key=lambda p: p.name.lower(),
        )
        for skill_dir in skill_dirs:
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                with open(skill_file, encoding="utf-8") as f:
                    content = f.read()
                frontmatter, _ = parse_frontmatter(content)
                name = frontmatter.get("name")
                description = frontmatter.get("description")
                if not name or not description:
                    continue
                enabled_config = cfg.get("skills.enabled", {})
                if isinstance(enabled_config, dict) and name in enabled_config:
                    if not enabled_config[name]:
                        continue
            except OSError:
                continue
            tools_dir = skill_dir / "tools"
            if tools_dir.is_dir():
                out.append(str(tools_dir.resolve()))

    return out


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
        default_dirs = tiered_dir_templates("skills")
        directories = parse_directory_list(
            cfg.get('skills.directories', default_dirs),
            default_dirs,
        )
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

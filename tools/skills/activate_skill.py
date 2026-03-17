import json
import os
from pathlib import Path
from utils.tool import register_tool
from utils.skills import skill_manager

def activate_skill(skill_name: str):
    """
    Activates a skill by loading its full instructions and listing its bundled resources.
    Args:
        skill_name: The name of the skill to activate.
    Returns:
        A JSON string containing the tool call details and the skill content.
    """
    skill = skill_manager.get_skill(skill_name)
    if not skill:
        result = f"Error: Skill '{skill_name}' not found."
    else:
        body = skill['body']
        base_dir = skill['base_dir']
        
        # Enumerate resources
        resources = []
        base_path = Path(base_dir)
        for root, _, files in os.walk(base_dir):
            for file in files:
                if file == 'SKILL.md':
                    continue
                file_path = Path(root) / file
                rel_path = file_path.relative_to(base_path)
                resources.append(str(rel_path))
                
        resources_xml = ""
        if resources:
            resources_xml = "\n<skill_resources>\n"
            for res in resources:
                resources_xml += f"  <file>{res}</file>\n"
            resources_xml += "</skill_resources>\n"
            
        content = f"""<skill_content name="{skill_name}">
{body}

Skill directory: {base_dir}
Relative paths in this skill are relative to the skill directory.
{resources_xml}
</skill_content>"""
        result = content

    return json.dumps({
        "function": "activate_skill",
        "arguments": {
            "skill_name": skill_name
        },
        "result": result
    }, indent=2)

register_tool('activate_skill', activate_skill, tags=['skills'])

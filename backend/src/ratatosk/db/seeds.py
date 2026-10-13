from pathlib import Path

import yaml
from ratatosk.db.models import SystemPrompt

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "assets" / "prompts"

#   --------------------------   #
#                                #
#   Set default system prompts   #
#                                #
#   --------------------------   #


def get_default_prompts() -> list[SystemPrompt]:
    """Read all markdown file, convert them and put them in the database"""

    prompts: list[SystemPrompt] = []
    if not PROMPTS_DIR.exists():
        return prompts

    for file in sorted(PROMPTS_DIR.glob("*.md")):
        text = file.read_text(encoding="utf-8")
        if text.count("---") == 2:
            parts = text.split("---", 2)[1:]
            yml = yaml.safe_load(parts[0]) or {}
            content = parts[1].strip()
            prompts.append(
                SystemPrompt(
                    name=yml.get("name"),
                    hierarchy=yml.get("hierarchy"),
                    description=yml.get("description"),
                    is_active=yml.get("is_active", True),
                    is_default=yml.get("is_default", True),
                    content=content,
                )
            )

    return prompts

"""Skill loader — loads skills from file-based SKILL.md definitions."""

from pathlib import Path
from typing import Any

import yaml
import re

SKILLS_DIR = Path(__file__).parent / "builtin"


class SkillLoader:
    """Load skills from file-based SKILL.md definitions."""

    _skills_cache: dict[str, dict] | None = None

    @classmethod
    def _parse_skill_md(cls, skill_path: Path) -> dict[str, Any] | None:
        """Parse a SKILL.md file and return skill definition."""
        skill_file = skill_path / "SKILL.md"
        if not skill_file.exists():
            return None

        content = skill_file.read_text(encoding="utf-8")

        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not frontmatter_match:
            return None

        try:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError:
            return None

        body = frontmatter_match.group(2)

        tools = []
        if "allowed-tools" in frontmatter:
            tools = frontmatter["allowed-tools"].split()

        return {
            "name": frontmatter.get("name", skill_path.name),
            "slug": frontmatter.get("name", skill_path.name),
            "description": frontmatter.get("description", ""),
            "category": frontmatter.get("category", "odr"),
            "system_prompt": body.strip(),
            "tools": tools,
            "is_free": frontmatter.get("is_free", True),
            "is_featured": frontmatter.get("is_featured", False),
            "config_schema": frontmatter.get("config_schema", {}),
            "path": str(skill_path),
        }

    @classmethod
    def load_all_skills(cls, force_reload: bool = False) -> dict[str, dict]:
        """Load all skills from the skills directory."""
        if cls._skills_cache is not None and not force_reload:
            return cls._skills_cache

        skills = {}
        if not SKILLS_DIR.exists():
            return skills

        for skill_dir in SKILLS_DIR.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                skill = cls._parse_skill_md(skill_dir)
                if skill:
                    skills[skill["slug"]] = skill

        cls._skills_cache = skills
        return skills

    @classmethod
    def get_skill(cls, slug: str) -> dict[str, Any] | None:
        """Get a specific skill by slug."""
        skills = cls.load_all_skills()
        return skills.get(slug)

    @classmethod
    def get_all_skill_slugs(cls) -> list[str]:
        """Get list of all available skill slugs."""
        return list(cls.load_all_skills().keys())

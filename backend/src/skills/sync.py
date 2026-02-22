"""Sync skills from SKILL.md files to database."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.logging import log
from src.skills.loader import SkillLoader
from src.db.models.skill import Skill


async def sync_skills_to_db(db: AsyncSession) -> dict:
    """Sync file-based skills to the database.

    Creates new skills or updates existing ones.

    Returns:
        Dict with created, updated, total counts.
    """
    file_skills = SkillLoader.load_all_skills(force_reload=True)
    created = 0
    updated = 0

    for slug, skill_data in file_skills.items():
        result = await db.execute(
            select(Skill).where(Skill.slug == slug)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.name = skill_data["name"]
            existing.description = skill_data["description"]
            existing.category = skill_data["category"]
            existing.system_prompt = skill_data["system_prompt"]
            existing.tools = skill_data["tools"]
            existing.config_schema = skill_data.get("config_schema", {})
            existing.is_active = True
            updated += 1
        else:
            skill = Skill(
                name=skill_data["name"],
                slug=slug,
                description=skill_data["description"],
                category=skill_data["category"],
                system_prompt=skill_data["system_prompt"],
                tools=skill_data["tools"],
                config_schema=skill_data.get("config_schema", {}),
                is_active=True,
                is_featured=skill_data.get("is_featured", False),
            )
            db.add(skill)
            created += 1

    await db.commit()

    result = {"created": created, "updated": updated, "total": len(file_skills)}
    log.info(f"Skills synced: {result}")
    return result

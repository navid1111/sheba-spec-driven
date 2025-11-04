"""
Template loading utilities for AI agents.

Provides functions to load versioned prompt templates from files.
"""
from pathlib import Path
from typing import Dict, Optional

from src.lib.logging import get_logger


logger = get_logger(__name__)


# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_template(
    agent_type: str,
    locale: str = "bn",
    version: int = 1
) -> Optional[str]:
    """
    Load prompt template from file.
    
    Args:
        agent_type: Agent type (smartengage, coachnova)
        locale: Language code (bn, en)
        version: Template version number
        
    Returns:
        Template content as string, or None if not found
        
    Example:
        >>> template = load_template("smartengage", "bn", 1)
        >>> prompt = template.format(customer_name="Karim", ...)
    """
    filename = f"{agent_type}_{locale}_v{version}.txt"
    template_path = TEMPLATES_DIR / filename
    
    try:
        if not template_path.exists():
            logger.warning(f"Template file not found: {template_path}")
            return None
        
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        logger.info(f"Loaded template: {filename}")
        return content
        
    except Exception as e:
        logger.error(f"Failed to load template {filename}: {e}")
        return None


def format_template(
    template: str,
    context: Dict[str, any],
    promo_section: str = ""
) -> str:
    """
    Format template with context variables.
    
    Args:
        template: Template string with {placeholders}
        context: Dictionary with values to substitute
        promo_section: Optional promo code section to inject
        
    Returns:
        Formatted template string
    """
    # Add promo_section to context if not already present
    format_context = {**context, "promo_section": promo_section}
    
    try:
        return template.format(**format_context)
    except KeyError as e:
        logger.error(f"Missing template variable: {e}")
        # Return template with missing variables as-is
        return template
    except Exception as e:
        logger.error(f"Template formatting error: {e}")
        return template


def get_template_version(agent_type: str, locale: str = "bn") -> int:
    """
    Get the latest template version available.
    
    Args:
        agent_type: Agent type
        locale: Language code
        
    Returns:
        Latest version number (default 1)
    """
    version = 1
    while True:
        filename = f"{agent_type}_{locale}_v{version + 1}.txt"
        if not (TEMPLATES_DIR / filename).exists():
            break
        version += 1
    
    return version

"""
Unit tests for template loader.
"""
import pytest
from pathlib import Path

from src.ai.template_loader import (
    load_template,
    format_template,
    get_template_version,
    TEMPLATES_DIR,
)


@pytest.mark.unit
def test_templates_directory_exists():
    """Template directory should exist."""
    assert TEMPLATES_DIR.exists()
    assert TEMPLATES_DIR.is_dir()


@pytest.mark.unit
def test_load_smartengage_bengali_v1():
    """Should load SmartEngage Bengali v1 template."""
    template = load_template("smartengage", "bn", 1)
    
    assert template is not None
    assert len(template) > 0
    assert "বাংলা" in template  # Should contain Bengali text
    assert "{customer_name}" in template  # Should have placeholders
    assert "{service_name_bn}" in template
    assert "{days_since}" in template


@pytest.mark.unit
def test_load_nonexistent_template():
    """Should return None for non-existent template."""
    template = load_template("nonexistent", "zz", 99)
    
    assert template is None


@pytest.mark.unit
def test_format_template_with_context():
    """Should format template with context variables."""
    template = "Hello {name}, your {service} is ready!"
    context = {
        "name": "Karim",
        "service": "cleaning"
    }
    
    result = format_template(template, context)
    
    assert result == "Hello Karim, your cleaning is ready!"


@pytest.mark.unit
def test_format_template_with_promo_section():
    """Should inject promo_section into template."""
    template = "Hello {name}! {promo_section}"
    context = {"name": "Karim"}
    promo = "Use code CLEAN20"
    
    result = format_template(template, context, promo)
    
    assert "Karim" in result
    assert "Use code CLEAN20" in result


@pytest.mark.unit
def test_format_template_missing_variable():
    """Should handle missing variables gracefully."""
    template = "Hello {name}, {missing_var}!"
    context = {"name": "Karim"}
    
    # Should not raise exception
    result = format_template(template, context)
    
    # Returns template as-is when variable missing
    assert "{missing_var}" in result or result == template


@pytest.mark.unit
def test_get_template_version_smartengage():
    """Should get latest SmartEngage Bengali version."""
    version = get_template_version("smartengage", "bn")
    
    assert version >= 1  # At least v1 should exist


@pytest.mark.unit
def test_template_file_structure():
    """SmartEngage v1 template should have proper structure."""
    template = load_template("smartengage", "bn", 1)
    
    assert template is not None
    
    # Should contain key Bengali sections
    assert "নির্দেশনা" in template or "উদাহরণ" in template
    
    # Should have placeholders
    placeholders = ["{customer_name}", "{service_name_bn}", "{days_since}", "{promo_section}"]
    for placeholder in placeholders:
        assert placeholder in template, f"Missing placeholder: {placeholder}"


@pytest.mark.unit
def test_template_encoding_utf8():
    """Template should load Bengali text correctly (UTF-8)."""
    template = load_template("smartengage", "bn", 1)
    
    assert template is not None
    
    # Check for common Bengali characters
    bengali_chars = ["আ", "ব", "ক", "গ", "র"]
    has_bengali = any(char in template for char in bengali_chars)
    assert has_bengali, "Template should contain Bengali characters"

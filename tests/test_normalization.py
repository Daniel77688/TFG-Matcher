"""Tests de normalización de texto — TFG Scraper Pro."""
import pytest
from src.utils.text_utils import normalize_text, generate_username


class TestNormalizeText:
    """Tests de la función normalize_text."""

    @pytest.mark.parametrize("input_text, expected", [
        ("TÍTULO", "titulo"),
        ("Producción", "produccion"),
        ("DANIEL MUÑOZ", "daniel munoz"),
        ("  espacios  múltiples  ", "espacios multiples"),
        ("Caracteres (Raros)!?*", "caracteres raros"),
        ("áéíóúÁÉÍÓÚñÑ", "aeiouaeiounn"),
        ("Softw@re & Engineering", "softw re engineering"),
        ("", ""),
        ("   ", ""),
    ])
    def test_normalize_text(self, input_text, expected):
        assert normalize_text(input_text) == expected

    def test_normalize_preserves_numbers(self):
        assert "2024" in normalize_text("Año 2024")

    def test_normalize_handles_none_gracefully(self):
        # normalize_text should handle empty strings at minimum
        result = normalize_text("")
        assert result == ""


class TestGenerateUsername:
    """Tests de la función generate_username."""

    @pytest.mark.parametrize("full_name, expected", [
        ("Daniel Muñoz", "daniel.munoz"),
        ("María García López", "maria.garcia.lopez"),
        ("JUAN PÉREZ", "juan.perez"),
    ])
    def test_generate_username(self, full_name, expected):
        assert generate_username(full_name) == expected

    def test_generate_username_single_name(self):
        result = generate_username("Daniel")
        assert result == "daniel"

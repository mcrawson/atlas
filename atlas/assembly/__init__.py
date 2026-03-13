"""Build utilities for ATLAS - code assembly and validation."""

from .code_assembler import CodeAssembler, assemble_code
from .validator import CodeValidator, validate_code, ValidationResult
from .html_expander import expand_html_templates, expand_document_html, ExpansionResult

__all__ = [
    "CodeAssembler", "assemble_code",
    "CodeValidator", "validate_code", "ValidationResult",
    "expand_html_templates", "expand_document_html", "ExpansionResult",
]

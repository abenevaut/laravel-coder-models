"""PHP code validation module for Laravel docs processing.

This module provides robust PHP code extraction and syntax validation
using php -l to ensure code validity in the training data.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# For Python 3.9+, tuple is in typing, for 3.10+ it's also available directly
try:
    from typing import Tuple
except ImportError:
    # Python 3.10+ - tuple is available directly
    pass


def extract_php_code_blocks(text: str) -> list[Tuple[str, str, str]]:
    """Extract PHP code blocks from text with robust pattern matching.
    
    Handles various code block formats:
    - Standard markdown: ```php ... ```
    - With language spec: ```php
    - Without language spec: ``` ... ```
    - Blade templates: ```blade ... ```
    - HTML+PHP: ```html ... ```
    - Inline PHP: <?php ... ?>
    
    Args:
        text: The text content to extract code from
        
    Returns:
        List of tuples: (code_content, block_type, original_block)
        where block_type is 'php', 'blade', 'html', 'inline', or 'unknown'
    """
    if not text:
        return []
    
    code_blocks = []
    
    # Pattern 1: Standard markdown code blocks with optional language
    # Matches: ```php
    #          code here
    #          ```
    # Also handles: ```php code here ``` (single line)
    code_block_pattern = r'```(\w*)\n?([\s\S]*?)\n?```'
    
    for match in re.finditer(code_block_pattern, text):
        lang = match.group(1).lower()
        code_content = match.group(2).strip()
        original_block = match.group(0)
        
        # Determine block type
        if lang in ['php', 'php8', 'php7']:
            block_type = 'php'
        elif lang == 'blade':
            block_type = 'blade'
        elif lang in ['html', 'html+php', 'htmlphp']:
            block_type = 'html'
        elif '<?php' in code_content or '<?=' in code_content:
            block_type = 'php'
        else:
            # Check if content looks like PHP
            if looks_like_php(code_content):
                block_type = 'php'
            else:
                block_type = lang if lang else 'unknown'
        
        # Only keep PHP-related blocks
        if block_type in ['php', 'blade', 'html']:
            code_blocks.append((code_content, block_type, original_block))
    
    # Pattern 2: Inline PHP tags (not in code blocks)
    # Only if they're not already captured in code blocks
    inline_php_pattern = r'(<?php[\s\S]*?>|<=.*?=>)'
    
    # Find inline PHP that's not already in captured code blocks
    # We need to check positions to avoid duplicates
    captured_ranges = []
    for match in re.finditer(code_block_pattern, text):
        captured_ranges.append((match.start(), match.end()))
    
    for match in re.finditer(inline_php_pattern, text):
        start, end = match.start(), match.end()
        
        # Check if this range overlaps with any captured code block
        is_in_block = any(
            not (end <= cb_start or start >= cb_end) 
            for cb_start, cb_end in captured_ranges
        )
        
        if not is_in_block:
            code_content = match.group(0).strip()
            if code_content and len(code_content) > 5:  # Minimum length
                code_blocks.append((code_content, 'inline', match.group(0)))
    
    return code_blocks


def looks_like_php(code: str) -> bool:
    """Heuristic to determine if code looks like PHP.
    
    Args:
        code: The code string to check
        
    Returns:
        True if code appears to be PHP
    """
    if not code or len(code.strip()) < 5:
        return False
    
    # Laravel-specific patterns
    laravel_patterns = [
        r'\bRoute::',
        r'\bModel::',
        r'\bDB::',
        r'\bAuth::',
        r'\bRequest::',
        r'\bResponse::',
        r'\bView::',
        r'\bValidator::',
        r'\bSchema::',
        r'\bEloquent\b',
        r'\bArtisan::',
        r'\bCache::',
        r'\bSession::',
        r'\bLog::',
        r'\bQueue::',
        r'\bEvent::',
        r'\bBroadcast::',
    ]
    
    for pattern in laravel_patterns:
        if re.search(pattern, code):
            return True
    
    # PHP syntax patterns
    php_patterns = [
        r'->\w+\s*\(',
        r'::\w+\s*\(',
        r'function\s+\w+\s*\(',
        r'class\s+\w+',
        r'namespace\s+',
        r'use\s+',
        r'\$\w+\s*=',
        r'new\s+\w+',
        r'\bif\s*\(',
        r'\bforeach\s*\(',
        r'\bwhile\s*\(',
        r'\bfor\s*\(',
        r'\breturn\s+',
    ]
    
    for pattern in php_patterns:
        if re.search(pattern, code):
            return True
    
    # Check for PHP tags
    if '<?php' in code or '<?=' in code or '<?' in code:
        return True
    
    return False


def extract_php_from_html(code: str) -> list[str]:
    """Extract PHP code from HTML/PHP mixed content.
    
    Args:
        code: HTML content that may contain PHP
        
    Returns:
        List of PHP code snippets found
    """
    php_snippets = []
    
    # Match PHP tags: <?php ... ?> or <? ... ?> or <?= ... ?>
    php_pattern = r'(?:<?php|<=)\s*([\s\S]*?)(?:\?>|=>)'
    
    for match in re.finditer(php_pattern, code):
        php_code = match.group(1).strip()
        if php_code:
            php_snippets.append(php_code)
    
    # If no PHP tags found but code contains Laravel patterns, return full code
    if not php_snippets and looks_like_php(code):
        php_snippets.append(code)
    
    return php_snippets


def is_valid_php(code: str, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """Validate PHP code syntax using php -l.
    
    Args:
        code: PHP code string to validate
        timeout: Timeout in seconds for the validation process
        
    Returns:
        Tuple of (is_valid, error_message)
        is_valid: True if code is syntactically valid
        error_message: Error message if invalid, None if valid
    """
    if not code or not code.strip():
        return False, "Empty code"
    
    try:
        # Prepare the code with proper PHP tags if not present
        code_to_check = code.strip()
        
        # Add PHP opening tag if not present
        if not code_to_check.startswith('<?'):
            code_to_check = f'<?php\n{code_to_check}'
        
        # Ensure it ends with a closing tag or semicolon
        if not code_to_check.endswith('?>'):
            # Check if it already has a closing tag
            if '?>' in code_to_check:
                # It has a closing tag somewhere, that's fine
                pass
            else:
                # Add closing tag
                code_to_check = f'{code_to_check}\n?>'
        
        # Run php -l
        result = subprocess.run(
            ['php', '-l'],
            input=code_to_check.encode('utf-8'),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        # Check the output
        stdout = result.stdout
        stderr = result.stderr
        return_code = result.returncode
        
        # php -l returns 0 for valid code, non-zero for invalid
        if return_code == 0 and 'No syntax errors detected' in stdout:
            return True, None
        else:
            # Extract error message
            error_msg = stdout or stderr or "Unknown syntax error"
            # Clean up the error message
            error_msg = error_msg.strip()
            return False, error_msg
            
    except subprocess.TimeoutExpired:
        return False, f"Validation timed out after {timeout} seconds"
    except FileNotFoundError:
        # php command not available
        # Fall back to basic syntax checking
        return basic_syntax_check(code)
    except Exception as e:
        return False, f"Validation error: {str(e)}"


def basic_syntax_check(code: str) -> Tuple[bool, Optional[str]]:
    """Basic PHP syntax check when php command is not available.
    
    This provides a fallback validation mechanism.
    
    Args:
        code: PHP code to check
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not code or not code.strip():
        return False, "Empty code"
    
    # Check for balanced braces
    open_braces = code.count('{')
    close_braces = code.count('}')
    if open_braces != close_braces:
        return False, f"Unbalanced braces: {open_braces} open, {close_braces} close"
    
    # Check for balanced parentheses
    open_parens = code.count('(')
    close_parens = code.count(')')
    if open_parens != close_parens:
        return False, f"Unbalanced parentheses: {open_parens} open, {close_parens} close"
    
    # Check for balanced square brackets
    open_brackets = code.count('[')
    close_brackets = code.count(']')
    if open_brackets != close_brackets:
        return False, f"Unbalanced brackets: {open_brackets} open, {close_brackets} close"
    
    # Check for unmatched quotes
    single_quotes = code.count("'")
    double_quotes = code.count('"')
    
    # This is a simplified check - doesn't handle escaped quotes
    if single_quotes % 2 != 0:
        return False, "Unmatched single quotes"
    if double_quotes % 2 != 0:
        return False, "Unmatched double quotes"
    
    return True, None


def validate_code_block(code: str, block_type: str = 'php') -> Tuple[bool, Optional[str], list[str]]:
    """Validate a code block and extract PHP snippets.
    
    Args:
        code: The code block content
        block_type: Type of the code block (php, blade, html, inline)
        
    Returns:
        Tuple of (is_valid, error_message, php_snippets)
        is_valid: True if all PHP snippets in the block are valid
        error_message: First error message if any
        php_snippets: List of extracted PHP code snippets
    """
    php_snippets = []
    
    if block_type == 'php':
        # Direct PHP code
        php_snippets = [code]
    elif block_type == 'blade':
        # Extract PHP from Blade templates
        # Blade uses @ directives and {{ }} expressions
        # Remove Blade syntax to extract underlying PHP
        blade_cleaned = re.sub(r'@\w+[\s\S]*?@end\w+', '', code)  # Remove @if...@endif etc.
        blade_cleaned = re.sub(r'{{[^}]*}}', '', blade_cleaned)  # Remove {{ }} echoes
        blade_cleaned = re.sub(r'{{{[^}]*}}}', '', blade_cleaned)  # Remove {{{ }}} raw echoes
        blade_cleaned = re.sub(r'@\w+', '', blade_cleaned)  # Remove @ directives
        
        # Extract any remaining PHP
        if looks_like_php(blade_cleaned):
            php_snippets = [blade_cleaned]
        else:
            # If no PHP after cleaning, try to extract PHP from original
            php_snippets = extract_php_from_html(code)
    elif block_type == 'html':
        # Extract PHP from HTML
        php_snippets = extract_php_from_html(code)
    elif block_type == 'inline':
        php_snippets = [code]
    else:
        # Unknown type, check if it looks like PHP
        if looks_like_php(code):
            php_snippets = [code]
    
    # If no PHP snippets found, consider it invalid
    if not php_snippets:
        return False, "No PHP code detected", []
    
    # Validate each PHP snippet
    all_valid = True
    first_error = None
    valid_snippets = []
    
    for snippet in php_snippets:
        is_valid, error_msg = is_valid_php(snippet)
        if not is_valid:
            all_valid = False
            if first_error is None:
                first_error = error_msg
            # Still keep the snippet for tracking
        valid_snippets.append(snippet)
    
    return all_valid, first_error, valid_snippets


def validate_section_code(section: dict) -> Tuple[bool, Optional[str], list[str]]:
    """Validate PHP code in a documentation section.
    
    Args:
        section: Section dict with 'body' key
        
    Returns:
        Tuple of (has_valid_code, error_message, all_code_snippets)
        has_valid_code: True if section contains valid PHP code
        error_message: First validation error if any
        all_code_snippets: List of all extracted PHP snippets
    """
    body = section.get('body', '')
    
    if not body:
        return False, None, []
    
    # Extract all code blocks
    code_blocks = extract_php_code_blocks(body)
    
    if not code_blocks:
        return False, None, []
    
    all_valid = True
    first_error = None
    all_snippets = []
    
    for code_content, block_type, original_block in code_blocks:
        is_valid, error_msg, snippets = validate_code_block(code_content, block_type)
        all_snippets.extend(snippets)
        
        if not is_valid:
            all_valid = False
            if first_error is None:
                first_error = error_msg
    
    # Consider valid if we have any PHP snippets, even if some are invalid
    # This is more lenient and allows partial code
    has_code = len(all_snippets) > 0
    
    return has_code, first_error, all_snippets


def validate_code(data: dict, **kwargs) -> dict:
    """Pipeline step: Validate PHP code in extracted sections.
    
    This step:
    1. Extracts PHP code blocks from each section
    2. Validates each block using php -l
    3. Adds validation metadata to sections
    4. Filters out sections with invalid code (optional)
    
    Input:  data["sections"] - list of section dicts
    Output: data["sections"] - list of section dicts with validation metadata
                  data["validation_errors"] - list of validation errors
    """
    doc_name = data.get("doc_name", "unknown")
    print(f"  [{doc_name}] Running: validate_code", file=sys.stderr)
    
    sections = data.get("sections", [])
    validation_errors = []
    valid_code_count = 0
    total_code_blocks = 0
    
    validated_sections = []
    
    for section in sections:
        section_body = section.get('body', '')
        
        # Check if section has PHP code blocks
        code_blocks = extract_php_code_blocks(section_body)
        
        if code_blocks:
            total_code_blocks += len(code_blocks)
            
            any_valid = False
            all_valid = True
            first_error = None
            all_snippets = []
            valid_block_count = 0
            
            for code_content, block_type, original_block in code_blocks:
                is_valid, error_msg, snippets = validate_code_block(code_content, block_type)
                all_snippets.extend(snippets)
                
                if is_valid:
                    valid_block_count += 1
                    any_valid = True
                else:
                    all_valid = False
                    if first_error is None:
                        first_error = error_msg
                    # Log the error
                    validation_errors.append({
                        'section_title': section.get('title', 'unknown'),
                        'block_type': block_type,
                        'error': error_msg,
                        'code': code_content[:100] + '...' if len(code_content) > 100 else code_content
                    })
            
            if all_snippets:
                valid_code_count += 1
            
            # Add validation metadata to section
            section['code_validation'] = {
                'has_code': len(code_blocks) > 0,
                'has_valid_code': any_valid,  # True if at least one block is valid
                'all_code_valid': all_valid,  # True if all blocks are valid
                'code_block_count': len(code_blocks),
                'valid_code_block_count': valid_block_count,
                'validation_errors': [first_error] if first_error else [],
                'extracted_php_snippets': all_snippets
            }
        else:
            # Section has no code blocks
            section['code_validation'] = {
                'has_code': False,
                'has_valid_code': False,
                'code_block_count': 0,
                'valid_code_block_count': 0,
                'validation_errors': [],
                'extracted_php_snippets': []
            }
        
        validated_sections.append(section)
    
    data["sections"] = validated_sections
    data["validation_errors"] = validation_errors
    data["code_validation_summary"] = {
        "total_code_blocks": total_code_blocks,
        "valid_code_count": valid_code_count
    }
    
    print(f"  [{doc_name}] Finished: validate_code (validated {len(sections)} sections, {total_code_blocks} code blocks, {valid_code_count} with valid code)", file=sys.stderr)
    return data


def check_php_available() -> bool:
    """Check if php command is available in the system."""
    try:
        result = subprocess.run(
            ['php', '-v'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
        return False


# Alias for backwards compatibility
validate_sections = validate_code

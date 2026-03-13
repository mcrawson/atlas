"""HTML Template Expander for ATLAS.

Expands repetitive patterns that LLMs abbreviate with comments like:
- <!-- Repeat for Tuesday to Sunday -->
- <!-- Repeat for 7 habits -->
- <!-- Repeat similar blocks for other days -->

This ensures document products (planners, trackers) are fully complete.
"""

import re
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("atlas.assembly.html_expander")


@dataclass
class ExpansionResult:
    """Result of HTML template expansion."""
    content: str
    expansions_made: list[str] = field(default_factory=list)


# Day patterns for weekly planners
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAYS_SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def expand_html_templates(html_content: str) -> ExpansionResult:
    """Expand abbreviated HTML patterns into complete content.

    Args:
        html_content: HTML string potentially containing repeat comments

    Returns:
        ExpansionResult with expanded content and list of expansions made
    """
    result = ExpansionResult(content=html_content)

    # Expansion 1: Days of the week
    result = _expand_days_pattern(result)

    # Expansion 2: Habit tracker rows
    result = _expand_habit_rows(result)

    # Expansion 3: Generic "repeat X times" patterns
    result = _expand_numeric_repeats(result)

    # Expansion 4: Task/checkbox lists
    result = _expand_task_lists(result)

    return result


def _expand_days_pattern(result: ExpansionResult) -> ExpansionResult:
    """Expand day-of-week repetition patterns."""
    content = result.content

    # Pattern: <!-- Repeat similar blocks for Tuesday to Sunday -->
    # or: <!-- Repeat for other days -->
    day_repeat_patterns = [
        r'<!--\s*[Rr]epeat\s+(?:similar\s+)?(?:blocks?\s+)?for\s+(?:Tuesday|other days).*?-->',
        r'<!--\s*[Rr]epeat\s+for\s+(?:the\s+)?(?:other|remaining)\s+days.*?-->',
    ]

    # Also catch very generic "repeat for other days" anywhere near day content
    day_repeat_patterns.append(r'<!--\s*[Rr]epeat\s+for\s+(?:the\s+)?other\s+days?\s*-->')

    for pattern in day_repeat_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            # Find the preceding day block (usually Monday)
            comment_pos = match.start()

            # Look for a day div/section before this comment
            day_block_pattern = r'(<div[^>]*class="day"[^>]*id="monday"[^>]*>.*?</div>)\s*' + re.escape(match.group())
            day_match = re.search(day_block_pattern, content, re.DOTALL | re.IGNORECASE)

            if day_match:
                monday_block = day_match.group(1)

                # Generate blocks for other days
                other_days_html = ""
                for day in DAYS_OF_WEEK[1:]:  # Skip Monday
                    day_block = monday_block
                    day_block = re.sub(r'id="monday"', f'id="{day.lower()}"', day_block, flags=re.IGNORECASE)
                    day_block = re.sub(r'>Monday<', f'>{day}<', day_block)
                    day_block = re.sub(r'Monday</h', f'{day}</h', day_block)
                    other_days_html += "\n            " + day_block

                # Replace the comment with actual days
                content = content.replace(match.group(), other_days_html)
                result.expansions_made.append(f"Expanded days: Tuesday-Sunday (6 blocks)")

    result.content = content
    return result


def _expand_habit_rows(result: ExpansionResult) -> ExpansionResult:
    """Expand habit tracker row patterns."""
    content = result.content

    # Pattern: various ways LLMs indicate habit row repetition
    # Each is (pattern, default_count) - default_count used if pattern doesn't capture a number
    habit_patterns = [
        (r'<!--\s*[Rr]epeat\s+for\s+(\d+)\s+(?:habits?|rows?)\s*-->', None),
        (r'<!--\s*[Rr]epeat\s+(\d+)\s+(?:more\s+)?(?:times?|rows?)\s*-->', None),
        (r'<!--\s*[Rr]epeat\s+(?:for\s+)?(\d+)\s+(?:more\s+)?rows?\s*-->', None),
        (r'<!--\s*(\d+)\s+rows?\s+for\s+(?:different\s+)?habits?\s*-->', None),  # "7 rows for different habits"
        (r'<!--\s*[Rr]epeat\s+for\s+more\s+habits?\s*-->', 7),  # generic - default to 7
    ]

    for pattern, default_count in habit_patterns:
        match = re.search(pattern, content)
        if match:
            # Try to extract number from pattern, else use default
            try:
                num_habits = int(match.group(1))
            except (IndexError, TypeError, ValueError):
                num_habits = default_count or 7

            comment_pos = match.start()
            comment_end = match.end()

            # Look for template row BEFORE or AFTER the comment
            before_comment = content[:comment_pos]
            after_comment = content[comment_end:]

            # Find the template row (flexible patterns)
            tr_patterns = [
                r'(<tr>\s*<td><input[^>]*placeholder="Habit \d+"[^>]*></td>.*?</tr>)',  # input with placeholder
                r'(<tr>\s*<td>Habit \d+</td>.*?</tr>)',  # text style
                r'(<tr>\s*<td><input[^>]*type="text"[^>]*></td>\s*(?:<td>.*?</td>\s*)+</tr>)',  # input text + checkboxes
            ]

            template_row = None

            # First look AFTER the comment (comment precedes template)
            for tr_pattern in tr_patterns:
                tr_match = re.search(tr_pattern, after_comment, re.DOTALL)
                if tr_match:
                    template_row = tr_match.group(1)
                    # Comment comes before template - replace comment AND add more rows after template
                    break

            # If not found after, look BEFORE the comment
            if not template_row:
                for tr_pattern in tr_patterns:
                    tr_matches = list(re.finditer(tr_pattern, before_comment, re.DOTALL))
                    if tr_matches:
                        template_row = tr_matches[-1].group(1)
                        break

            if template_row:
                # Generate additional habit rows (2 through num_habits)
                additional_rows = ""
                for i in range(2, num_habits + 1):
                    new_row = re.sub(r'Habit \d+', f'Habit {i}', template_row)
                    new_row = re.sub(r'placeholder="Habit \d+"', f'placeholder="Habit {i}"', new_row)
                    additional_rows += "\n                    " + new_row

                # If comment was BEFORE the template row, insert rows after the template
                # by finding template row and appending
                if template_row in after_comment:
                    # Remove the comment, then add rows after the template
                    content = content.replace(match.group(), "")  # Remove comment
                    content = content.replace(template_row, template_row + additional_rows)
                else:
                    # Comment was after template row - replace comment with rows
                    content = content.replace(match.group(), additional_rows)

                result.expansions_made.append(f"Expanded habit rows: {num_habits - 1} additional rows")

    result.content = content
    return result


def _expand_numeric_repeats(result: ExpansionResult) -> ExpansionResult:
    """Expand generic numeric repeat patterns."""
    content = result.content

    # Pattern: <!-- Repeat X more times -->
    pattern = r'<!--\s*[Rr]epeat\s+(\d+)\s+more\s+times?\s*-->'

    for match in re.finditer(pattern, content):
        num_repeats = int(match.group(1))
        comment_pos = match.start()

        # Find preceding list item or row
        before_comment = content[:comment_pos]

        # Try to find <li> pattern
        li_pattern = r'(<li>.*?</li>)\s*$'
        li_match = re.search(li_pattern, before_comment, re.DOTALL)

        if li_match:
            template = li_match.group(1)
            additional = ""
            for i in range(num_repeats):
                additional += "\n                    " + template
            content = content.replace(match.group(), additional)
            result.expansions_made.append(f"Expanded list items: {num_repeats} additional")

    result.content = content
    return result


def _expand_task_lists(result: ExpansionResult) -> ExpansionResult:
    """Ensure task lists have proper checkbox structure."""
    content = result.content

    # Find any day blocks that only have placeholder text
    # Pattern: Task 1, Task 2 etc should become proper checkboxes if not already

    # This is more of a validation/fix than expansion
    # Check if we have proper checkbox inputs
    if '<input type="checkbox">' not in content and 'checkbox' in content.lower():
        # Try to add proper checkbox markup
        content = re.sub(
            r'<li>\s*Task\s*(\d+)\s*</li>',
            r'<li><input type="checkbox"> Task \1</li>',
            content
        )
        if '<input type="checkbox">' in content:
            result.expansions_made.append("Added checkbox inputs to task items")

    result.content = content
    return result


def expand_document_html(files: dict[str, str]) -> dict[str, str]:
    """Expand all HTML files in a file dictionary.

    Args:
        files: Dictionary of filename -> content

    Returns:
        Dictionary with expanded HTML content
    """
    expanded_files = {}

    for name, content in files.items():
        if name.endswith('.html') or name.endswith('.htm'):
            result = expand_html_templates(content)
            expanded_files[name] = result.content

            if result.expansions_made:
                logger.info(f"[HTMLExpander] {name}: {', '.join(result.expansions_made)}")
        else:
            expanded_files[name] = content

    return expanded_files

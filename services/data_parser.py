import json
import re

def parse_json(raw_output):
    """
    Parse  JSON or JSON-like string from LLM output.
    Handles cases with markdown (```json ... ```), ####, '''json, or direct JSON.
    Returns a dict or None if parsing fails.
    """
    # 1. Remove markdown/code block wrappers
    cleaned = raw_output.strip()
    # Remove ```json ... ```
    cleaned = re.sub(r"```json(.*?)```", r"\1", cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Remove ``` ... ```
    cleaned = re.sub(r"```(.*?)```", r"\1", cleaned, flags=re.DOTALL)
    # Remove #### ... ####
    cleaned = re.sub(r"#+\s*json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"#+", "", cleaned)
    # Remove '''json ... '''
    cleaned = re.sub(r"'''json(.*?)'''", r"\1", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"'''(.*?)'''", r"\1", cleaned, flags=re.DOTALL)
    # Remove leading/trailing whitespace and newlines
    cleaned = cleaned.strip()

    # 2. Try to find the first {...} JSON object in the string
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)

    # 3. Try parsing
    try:
        return json.loads(cleaned)
    except Exception as e:
        # Try to fix common issues (single quotes, trailing commas)
        fixed = cleaned.replace("'", '"')
        fixed = re.sub(r",\s*}", "}", fixed)
        fixed = re.sub(r",\s*]", "]", fixed)
        try:
            return json.loads(fixed)
        except Exception as e2:
            return None


def parse_list(raw_output):
    """
    Parse a Python list from LLM output.
    Handles direct lists, markdown/code blocks (```python ... ```), and other wrappers.
    Returns a Python list or None if parsing fails.
    """
    cleaned = raw_output.strip()
    # Remove ```python ... ```
    cleaned = re.sub(r"```python(.*?)```", r"\1", cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Remove ``` ... ```
    cleaned = re.sub(r"```(.*?)```", r"\1", cleaned, flags=re.DOTALL)
    # Remove '''python ... '''
    cleaned = re.sub(r"'''python(.*?)'''", r"\1", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"'''(.*?)'''", r"\1", cleaned, flags=re.DOTALL)
    # Remove #### ... ####
    cleaned = re.sub(r"#+\s*python\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"#+", "", cleaned)
    cleaned = cleaned.strip()

    # Try to find the first [...] list in the string
    match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)

    # Try parsing as JSON list
    try:
        return json.loads(cleaned)
    except Exception:
        # Try to eval as Python list (safe)
        try:
            import ast
            result = ast.literal_eval(cleaned)
            if isinstance(result, list):
                return result
        except Exception:
            return



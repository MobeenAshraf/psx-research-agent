"""JSON parsing utilities for LLM responses."""

import json
from typing import Dict, Any


class JSONParser:
    """Parses JSON responses from LLM, handling various formatting issues."""
    
    @staticmethod
    def parse_response(response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM, handling various formatting issues.
        
        Args:
            response: Raw response string from LLM
            
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            json.JSONDecodeError: If JSON cannot be parsed
            ValueError: If no JSON object found
        """
        if not response or not response.strip():
            raise ValueError("Empty response received")
        
        original_response = response
        
        # Step 1: Remove markdown code blocks if present
        response_clean = response.strip()
        if "```json" in response_clean:
            start = response_clean.find("```json") + 7
            end = response_clean.find("```", start)
            if end > start:
                response_clean = response_clean[start:end].strip()
        elif "```" in response_clean:
            start = response_clean.find("```") + 3
            end = response_clean.find("```", start)
            if end > start:
                response_clean = response_clean[start:end].strip()
        
        # Step 2: Find JSON object boundaries
        start_idx = response_clean.find("{")
        end_idx = response_clean.rfind("}")
        
        # Check if response appears truncated (no closing brace)
        if start_idx >= 0 and end_idx <= start_idx:
            # Try to detect if we're in the middle of a value
            last_comma = response_clean.rfind(",")
            last_colon = response_clean.rfind(":")
            if last_colon > last_comma and last_colon > start_idx:
                # We're likely in the middle of a value - this is truncated
                raise ValueError(
                    f"Response appears truncated - no closing brace found. "
                    f"Response ends with: {repr(response_clean[-100:])}"
                )
        
        if start_idx < 0 or end_idx <= start_idx:
            # Attempt to auto-wrap key/value pairs into JSON
            candidate = []
            for line in response_clean.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("- "):
                    stripped = stripped[2:].strip()
                candidate.append(stripped)
            
            if candidate:
                candidate_text = "\n".join(candidate)
                if not candidate_text.startswith("{"):
                    candidate_text = "{\n" + candidate_text
                if not candidate_text.rstrip().endswith("}"):
                    candidate_text = candidate_text.rstrip().rstrip(",") + "\n}"
                try:
                    return json.loads(candidate_text)
                except json.JSONDecodeError:
                    pass
            
            raise ValueError(
                "No valid JSON object found. Response preview: "
                f"{repr(response_clean[:200])}"
            )
        
        # Extract just the JSON part
        response_clean = response_clean[start_idx:end_idx + 1]
        
        # Step 3: Aggressively clean whitespace
        if response_clean.startswith('\n') or response_clean.startswith('\r') or response_clean.startswith(' '):
            first_brace = response_clean.find('{')
            if first_brace > 0:
                response_clean = response_clean[first_brace:]
        
        response_clean = response_clean.rstrip()
        
        # Step 4: Try parsing
        try:
            return json.loads(response_clean)
        except json.JSONDecodeError as json_err:
            # Check if error is due to incomplete JSON (truncation)
            if json_err.pos >= len(response_clean) - 10:
                # Error near the end - likely truncation
                raise ValueError(
                    f"JSON appears truncated. Error at position {json_err.pos} of {len(response_clean)}. "
                    f"Response ends with: {repr(response_clean[-200:])}"
                ) from json_err
            
            # Step 5: Try line-by-line extraction with proper brace counting
            lines = original_response.split('\n')
            json_lines = []
            brace_count = 0
            in_json = False
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not in_json:
                    if '{' in stripped:
                        brace_pos = stripped.find('{')
                        json_lines = [stripped[brace_pos:]]
                        brace_count = stripped[brace_pos:].count('{') - stripped[brace_pos:].count('}')
                        in_json = True
                        if brace_count <= 0:
                            try:
                                return json.loads(stripped[brace_pos:])
                            except json.JSONDecodeError:
                                pass
                else:
                    json_lines.append(line)
                    brace_count += line.count('{') - line.count('}')
                    if brace_count <= 0:
                        break
            
            if json_lines:
                response_clean = '\n'.join(json_lines)
                first_line = json_lines[0]
                if first_line.strip().startswith('{'):
                    json_lines[0] = first_line[first_line.find('{'):]
                    response_clean = '\n'.join(json_lines)
                
                try:
                    return json.loads(response_clean)
                except json.JSONDecodeError as e2:
                    try:
                        start = response_clean.find('{')
                        end = response_clean.rfind('}')
                        if start >= 0 and end > start:
                            return json.loads(response_clean[start:end+1])
                    except json.JSONDecodeError:
                        pass
            
            error_msg = (
                f"JSON parsing failed after all cleanup attempts.\n"
                f"Original error: {str(json_err)}\n"
                f"Error position: {json_err.pos}\n"
                f"Response length: {len(original_response)}\n"
                f"Cleaned response preview (first 500 chars):\n{repr(response_clean[:500])}"
            )
            raise json.JSONDecodeError(error_msg, response_clean, json_err.pos)


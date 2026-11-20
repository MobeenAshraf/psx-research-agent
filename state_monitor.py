"""Monitor LangGraph state files and stream updates via SSE."""

import json
import time
import asyncio
from pathlib import Path
from financial.result_paths import DEFAULT_RESULTS_DIRECTORY, model_directory
from typing import Dict, Any, AsyncIterator, Optional


def find_states_directory(symbol: str, extraction_model: Optional[str] = None, analysis_model: Optional[str] = None) -> Path:
    """
    Find the states directory for a symbol and model combination.
    If model is not provided, checks all model directories and returns the one with most recent states.
    """
    symbol_upper = symbol.upper()
    base_dir = DEFAULT_RESULTS_DIRECTORY / symbol_upper
    
    if extraction_model or analysis_model:
        model_key = model_directory(extraction_model, analysis_model)
        return base_dir / model_key / "states"
    
    # If no model specified, check all model directories and find the most recent
    if not base_dir.exists():
        return base_dir / "states"
    
    most_recent_dir = None
    most_recent_time = 0
    
    # Check old location (for backward compatibility)
    old_states_dir = base_dir / "states"
    if old_states_dir.exists():
        state_files = list(old_states_dir.glob("*_state.json"))
        if state_files:
            most_recent_file = max(state_files, key=lambda p: p.stat().st_mtime)
            most_recent_time = most_recent_file.stat().st_mtime
            most_recent_dir = old_states_dir
    
    # Check all model-specific directories
    for model_dir in base_dir.iterdir():
        if model_dir.is_dir() and model_dir.name != "states":
            states_dir = model_dir / "states"
            if states_dir.exists():
                state_files = list(states_dir.glob("*_state.json"))
                if state_files:
                    most_recent_file = max(state_files, key=lambda p: p.stat().st_mtime)
                    file_time = most_recent_file.stat().st_mtime
                    if file_time > most_recent_time:
                        most_recent_time = file_time
                        most_recent_dir = states_dir
    
    if most_recent_dir:
        return most_recent_dir
    
    return base_dir / "states"


def read_states(states_dir: Path) -> Dict[str, Any]:
    """Read files belonging to the latest run in the directory."""
    states = {}
    for state_file in sorted(states_dir.glob("*_state.json")):
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        step = state_file.stem.removesuffix("_state")
        states[step] = state
    run_id = states.get("00_initial", {}).get("run_id")
    if run_id is None:
        return {}
    return {step: state for step, state in states.items() if state.get("run_id") == run_id}


def get_state_progress(step_name: str) -> int:
    """
    Map state step name to progress percentage.
    
    Args:
        step_name: State step name (e.g., '00_initial', '01_extract')
        
    Returns:
        Progress percentage (0-100)
    """
    progress_map = {
        '00_initial': 0,
        '01_extract': 20,
        '02_calculate': 40,
        '03_validate': 60,
        '04_analyze': 80,
        '05_format': 90,
        '99_final': 100
    }
    return progress_map.get(step_name, 0)


async def stream_states(
    symbol: str, 
    poll_interval: float = 1.5,
    extraction_model: Optional[str] = None,
    analysis_model: Optional[str] = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream state updates as they become available.
    
    Args:
        symbol: Stock symbol
        poll_interval: How often to poll for new states (seconds)
        extraction_model: Optional extraction model (for model-specific directory)
        analysis_model: Optional analysis model (for model-specific directory)
        
    Yields:
        Dictionary with state data
    """
    symbol_upper = symbol.upper()
    states_dir = find_states_directory(symbol_upper, extraction_model, analysis_model)
    
    if not states_dir.exists():
        states_dir.mkdir(parents=True, exist_ok=True)
    
    seen_states = set()
    current_run = None
    max_wait_time = 300
    start_time = time.time()
    
    while True:
        if time.time() - start_time > max_wait_time:
            yield {
                'type': 'timeout',
                'message': 'Analysis timeout - no updates received'
            }
            break
        
        states = read_states(states_dir)
        run_id = states.get("00_initial", {}).get("run_id")
        if run_id != current_run:
            seen_states.clear()
            current_run = run_id

        for step_name, state_data in states.items():
            if step_name in seen_states:
                continue

            try:
                progress = get_state_progress(step_name)
                
                yield {
                    'type': 'state',
                    'step': step_name,
                    'progress': progress,
                    'data': state_data,
                    'timestamp': state_data.get('timestamp', ''),
                    'token_usage': state_data.get('token_usage')
                }
                
                seen_states.add(step_name)
                
                if step_name == '99_final':
                    if state_data.get('errors'):
                        yield {
                            'type': 'error',
                            'step': step_name,
                            'error': ' | '.join(state_data['errors']),
                        }
                        return
                    yield {
                        'type': 'complete',
                        'message': 'Analysis complete',
                        'final_state': state_data,
                        'token_usage': state_data.get('token_usage')
                    }
                    return
            except Exception as e:
                yield {
                    'type': 'error',
                    'step': step_name,
                    'error': str(e)
                }
        
        await asyncio.sleep(poll_interval)


def get_current_states(
    symbol: str,
    extraction_model: Optional[str] = None,
    analysis_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all current states for a symbol and model combination.
    
    Args:
        symbol: Stock symbol
        extraction_model: Optional extraction model (for model-specific directory)
        analysis_model: Optional analysis model (for model-specific directory)
        
    Returns:
        Dictionary with all states and progress
    """
    symbol_upper = symbol.upper()
    states_dir = find_states_directory(symbol_upper, extraction_model, analysis_model)
    
    if not states_dir.exists():
        return {
            'symbol': symbol_upper,
            'states': {},
            'progress': 0,
            'status': 'not_started'
        }
    
    states = read_states(states_dir)

    if not states:
        return {
            'symbol': symbol_upper,
            'states': {},
            'progress': 0,
            'status': 'not_started'
        }
    
    latest_step = max(states.keys())
    progress = get_state_progress(latest_step)
    
    final_state = states.get("99_final")
    status = "in_progress"
    if final_state:
        status = "error" if final_state.get("errors") else "complete"
    
    return {
        'symbol': symbol_upper,
        'states': states,
        'progress': progress,
        'latest_step': latest_step,
        'status': status
    }


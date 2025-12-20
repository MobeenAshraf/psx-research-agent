"""Monitor LangGraph state files and stream updates via SSE."""

import json
import time
import asyncio
import re
from pathlib import Path
from typing import Dict, Any, AsyncIterator, Optional


def _generate_model_key(
    extraction_model: Optional[str] = None, analysis_model: Optional[str] = None
) -> str:
    """Generate model key for directory naming (same logic as FileResultRepository)."""
    extraction = extraction_model or "default"
    analysis = analysis_model or "default"
    
    model_key = f"{extraction}_{analysis}"
    model_key = model_key.replace("/", "_")
    model_key = re.sub(r'[^a-zA-Z0-9_-]', '_', model_key)
    model_key = re.sub(r'_+', '_', model_key)
    model_key = model_key.strip('_')
    
    return model_key


def find_states_directory(symbol: str, extraction_model: Optional[str] = None, analysis_model: Optional[str] = None) -> Path:
    """
    Find the states directory for a symbol and model combination.
    If model is not provided, checks all model directories and returns the one with most recent states.
    """
    symbol_upper = symbol.upper()
    base_dir = Path("data/results") / symbol_upper
    
    if extraction_model or analysis_model:
        model_key = _generate_model_key(extraction_model, analysis_model)
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
    max_wait_time = 300
    start_time = time.time()
    
    while True:
        if time.time() - start_time > max_wait_time:
            yield {
                'type': 'timeout',
                'message': 'Analysis timeout - no updates received'
            }
            break
        
        state_files = sorted(states_dir.glob("*_state.json"))
        
        for state_file in state_files:
            step_name = state_file.stem.replace('_state', '')
            
            if step_name in seen_states:
                continue
            
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
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
    
    states = {}
    state_files = sorted(states_dir.glob("*_state.json"))
    
    for state_file in state_files:
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                step_name = state_file.stem.replace('_state', '')
                states[step_name] = state_data
        except Exception:
            continue
    
    if not states:
        return {
            'symbol': symbol_upper,
            'states': {},
            'progress': 0,
            'status': 'not_started'
        }
    
    latest_step = max(states.keys())
    progress = get_state_progress(latest_step)
    
    status = 'complete' if '99_final' in states else 'in_progress'
    
    return {
        'symbol': symbol_upper,
        'states': states,
        'progress': progress,
        'latest_step': latest_step,
        'status': status
    }


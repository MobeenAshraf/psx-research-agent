"""Monitor LangGraph state files and stream updates via SSE."""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, AsyncIterator


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


async def stream_states(symbol: str, poll_interval: float = 1.5) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream state updates as they become available.
    
    Args:
        symbol: Stock symbol
        poll_interval: How often to poll for new states (seconds)
        
    Yields:
        Dictionary with state data
    """
    symbol_upper = symbol.upper()
    states_dir = Path("data/results") / symbol_upper / "states"
    
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


def get_current_states(symbol: str) -> Dict[str, Any]:
    """
    Get all current states for a symbol.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Dictionary with all states and progress
    """
    symbol_upper = symbol.upper()
    states_dir = Path("data/results") / symbol_upper / "states"
    
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


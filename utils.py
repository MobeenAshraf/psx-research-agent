"""Shared utilities for the project."""

import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

ANALYTICS_DIR = Path("data/analytics")
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="analytics")


def find_repo_root() -> Path:
    """Find the repository root by looking for pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def _write_log_entry_sync(log_entry: Dict[str, Any]) -> None:
    """Synchronous file write (runs in thread pool)."""
    try:
        log_file = ANALYTICS_DIR / f"api_usage_{datetime.utcnow().strftime('%Y-%m-%d')}.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write analytics log: {e}")


async def log_api_request(
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    request_data: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    token_usage: Optional[Dict[str, Any]] = None,
    extraction_tokens: Optional[int] = None,
    analysis_tokens: Optional[int] = None,
    extraction_price: Optional[float] = None,
    analysis_price: Optional[float] = None,
    total_cost: Optional[float] = None
) -> None:
    """
    Log API request for analytics (non-blocking).
    
    Args:
        endpoint: API endpoint path
        method: HTTP method
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        request_data: Request body data (symbol, models, etc.)
        error: Error message if any
        token_usage: Token usage data if available
        extraction_tokens: Token count for extraction step
        analysis_tokens: Token count for analysis step
        extraction_price: Cost for extraction step
        analysis_price: Cost for analysis step
        total_cost: Total cost
    """
    try:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "request_data": request_data or {},
            "error": error,
            "token_usage": token_usage,
            "extraction_tokens": extraction_tokens,
            "analysis_tokens": analysis_tokens,
            "extraction_price": extraction_price,
            "analysis_price": analysis_price,
            "total_cost": total_cost
        }
        
        loop = asyncio.get_event_loop()
        loop.run_in_executor(_executor, _write_log_entry_sync, log_entry)
            
    except Exception as e:
        logger.error(f"Failed to log API request: {e}")


def get_analytics_summary(days: int = 7) -> Dict[str, Any]:
    """
    Get analytics summary for the last N days.
    
    Args:
        days: Number of days to summarize
        
    Returns:
        Dictionary with analytics summary
    """
    summary = {
        "total_requests": 0,
        "endpoints": {},
        "status_codes": {},
        "avg_duration_ms": 0,
        "errors": 0,
        "token_usage": {
            "total_tokens": 0,
            "total_requests_with_tokens": 0
        },
        "costs": {
            "total_cost": 0.0,
            "total_requests_with_cost": 0,
            "avg_cost_per_request": 0.0,
            "cost_by_endpoint": {}
        }
    }
    
    durations = []
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    try:
        for log_file in ANALYTICS_DIR.glob("api_usage_*.jsonl"):
            file_date_str = log_file.stem.replace("api_usage_", "")
            try:
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                if file_date < cutoff_date:
                    continue
            except ValueError:
                continue
            
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        summary["total_requests"] += 1
                        
                        endpoint = entry.get("endpoint", "unknown")
                        summary["endpoints"][endpoint] = summary["endpoints"].get(endpoint, 0) + 1
                        
                        status = entry.get("status_code", 0)
                        summary["status_codes"][status] = summary["status_codes"].get(status, 0) + 1
                        
                        if status >= 400:
                            summary["errors"] += 1
                        
                        duration = entry.get("duration_ms", 0)
                        if duration > 0:
                            durations.append(duration)
                        
                        token_usage = entry.get("token_usage")
                        if token_usage:
                            total = token_usage.get("cumulative", {}).get("total_tokens", 0)
                            if total > 0:
                                summary["token_usage"]["total_tokens"] += total
                                summary["token_usage"]["total_requests_with_tokens"] += 1
                        
                        total_cost = entry.get("total_cost")
                        if total_cost is not None and total_cost > 0:
                            summary["costs"]["total_cost"] += total_cost
                            summary["costs"]["total_requests_with_cost"] += 1
                            
                            endpoint = entry.get("endpoint", "unknown")
                            if endpoint not in summary["costs"]["cost_by_endpoint"]:
                                summary["costs"]["cost_by_endpoint"][endpoint] = 0.0
                            summary["costs"]["cost_by_endpoint"][endpoint] += total_cost
                                
                    except json.JSONDecodeError:
                        continue
                        
    except Exception as e:
        logger.error(f"Failed to read analytics summary: {e}")
    
    if durations:
        summary["avg_duration_ms"] = round(sum(durations) / len(durations), 2)
    
    if summary["costs"]["total_requests_with_cost"] > 0:
        summary["costs"]["avg_cost_per_request"] = round(
            summary["costs"]["total_cost"] / summary["costs"]["total_requests_with_cost"],
            6
        )
    
    return summary


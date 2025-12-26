"""FastAPI application for PSX Stock Analysis Frontend."""

import json
import time
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from pydantic import BaseModel, Field
from typing import Optional
from pathlib import Path
from starlette.middleware.base import BaseHTTPMiddleware
from routes import get_technical_analysis, check_latest_report, run_financial_analysis, get_llm_decision
from financial.config.model_config import ModelConfig
from state_monitor import stream_states, get_current_states
from utils import log_api_request
from financial.config.cost_calculator import calculate_cost


app = FastAPI(
    title="PSX Stock Analysis API",
    description="API for technical and financial analysis of PSX stocks",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://psx-research-agent-421423162806.asia-southeast1.run.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AnalyticsMiddleware(BaseHTTPMiddleware):
    """Middleware to track API usage for analytics (non-blocking, minimal overhead)."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        endpoint = request.url.path
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        if endpoint.startswith("/api/"):
            error = None
            if response.status_code >= 400:
                error = f"HTTP {response.status_code}"
            
            extraction_tokens = None
            analysis_tokens = None
            extraction_price = None
            analysis_price = None
            total_cost = None
            token_usage_data = None
            
            if response.status_code == 200 and (
                endpoint == "/api/financial-analysis/check" or 
                endpoint.startswith("/api/financial-analysis/result/")
            ):
                try:
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk
                    
                    if body:
                        response_data = json.loads(body.decode())
                        token_usage_data = response_data.get("token_usage")
                        
                        if token_usage_data:
                            steps = token_usage_data.get("steps", {})
                            extract_step = steps.get("extract", {})
                            analyze_step = steps.get("analyze", {})
                            
                            if extract_step:
                                extraction_tokens = extract_step.get("total_tokens")
                                extraction_price = response_data.get("extraction_cost")
                            
                            if analyze_step:
                                analysis_tokens = analyze_step.get("total_tokens")
                                analysis_price = response_data.get("analysis_cost")
                            
                            total_cost = response_data.get("total_cost")
                    
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type
                    )
                except (json.JSONDecodeError, KeyError, Exception):
                    pass
            
            asyncio.create_task(log_api_request(
                endpoint=endpoint,
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration_ms,
                request_data={},
                error=error,
                token_usage=token_usage_data,
                extraction_tokens=extraction_tokens,
                analysis_tokens=analysis_tokens,
                extraction_price=extraction_price,
                analysis_price=analysis_price,
                total_cost=total_cost
            ))
        
        return response


app.add_middleware(AnalyticsMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy"}


static_dir = Path("static")
if static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    
    class NoCacheStaticFiles(StaticFiles):
        """Static files with no-cache headers for development."""
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        
        async def __call__(self, scope, receive, send):
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    headers = dict(message.get("headers", []))
                    headers[b"cache-control"] = b"no-cache, no-store, must-revalidate"
                    headers[b"pragma"] = b"no-cache"
                    headers[b"expires"] = b"0"
                    message["headers"] = list(headers.items())
                await send(message)
            
            await super().__call__(scope, receive, send_wrapper)
    
    app.mount("/static", NoCacheStaticFiles(directory="static"), name="static")


class TechnicalAnalysisRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)


class FinancialAnalysisRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    pdf_text: Optional[str] = None
    pdf_url: Optional[str] = None
    extraction_model: Optional[str] = "auto"
    analysis_model: Optional[str] = "auto"


class LLMDecisionRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    extraction_model: Optional[str] = "auto"
    analysis_model: Optional[str] = "auto"
    decision_model: Optional[str] = "auto"


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main frontend page."""
    html_file = Path("templates/index.html")
    if html_file.exists():
        html_content = html_file.read_text(encoding='utf-8')
        
        # Add cache-busting query parameter to JS file based on file modification time
        js_file = static_dir / "app.js"
        if js_file.exists():
            import os
            mtime = int(os.path.getmtime(js_file))
            html_content = html_content.replace(
                '/static/app.js',
                f'/static/app.js?v={mtime}'
            )
        
        return HTMLResponse(
            content=html_content,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.post("/api/technical-analysis")
async def technical_analysis(request: TechnicalAnalysisRequest):
    """
    Perform technical analysis on a stock.
    
    Args:
        request: Request with stock symbol
        
    Returns:
        Technical analysis results
    """
    result = get_technical_analysis(request.symbol)
    
    if result.get('status') == 'error':
        raise HTTPException(status_code=500, detail=result.get('error', 'Analysis failed'))
    
    return result


@app.post("/api/financial-analysis/check")
async def check_financial_analysis(request: FinancialAnalysisRequest):
    """
    Check if latest financial report exists.
    
    Args:
        request: Request with stock symbol
        
    Returns:
        Report status and data if exists
    """
    result = check_latest_report(
        request.symbol,
        extraction_model=request.extraction_model,
        analysis_model=request.analysis_model
    )
    return result


@app.post("/api/financial-analysis/run")
async def run_financial_analysis_route(request: FinancialAnalysisRequest):
    """
    Start financial analysis in background.
    
    Args:
        request: Request with stock symbol
        
    Returns:
        Status indicating analysis started
    """
    result = run_financial_analysis(
        request.symbol,
        pdf_text=request.pdf_text,
        pdf_url=request.pdf_url,
        extraction_model=request.extraction_model,
        analysis_model=request.analysis_model
    )
    
    if result.get('status') == 'error':
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to start analysis'))
    
    return result


@app.get("/api/financial-analysis/stream/{symbol}")
async def stream_financial_analysis(
    symbol: str,
    extraction_model: Optional[str] = None,
    analysis_model: Optional[str] = None
):
    """
    Stream financial analysis state updates via Server-Sent Events.
    
    Args:
        symbol: Stock symbol
        extraction_model: Optional extraction model (for model-specific directory)
        analysis_model: Optional analysis model (for model-specific directory)
        
    Returns:
        SSE stream of state updates
    """
    # Normalize model names to match directory structure
    # Always normalize (including "auto") to match how directories are created
    normalized_extraction = ModelConfig.normalize_model_name(
        extraction_model or "auto", 
        is_extraction=True
    )
    normalized_analysis = ModelConfig.normalize_model_name(
        analysis_model or "auto", 
        is_extraction=False
    )
    
    async def event_generator():
        try:
            async for state_update in stream_states(
                symbol, 
                extraction_model=normalized_extraction, 
                analysis_model=normalized_analysis
            ):
                data = json.dumps(state_update)
                yield f"data: {data}\n\n"
                
                if state_update.get('type') == 'complete':
                    break
        except Exception as e:
            error_data = json.dumps({
                'type': 'error',
                'error': str(e)
            })
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/financial-analysis/status/{symbol}")
async def get_financial_analysis_status(symbol: str):
    """
    Get current financial analysis status.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Current status and states
    """
    result = get_current_states(symbol)
    return result


@app.get("/api/financial-analysis/result/{symbol}")
async def get_financial_analysis_result(symbol: str):
    """
    Get final financial analysis result.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Final analysis report
    """
    from state_monitor import find_states_directory
    
    symbol_upper = symbol.upper()
    states_dir = find_states_directory(symbol_upper)
    final_state_file = states_dir / "99_final_state.json"
    
    if not final_state_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Analysis not complete or not found"
        )
    
    try:
        with open(final_state_file, 'r', encoding='utf-8') as f:
            final_state = json.load(f)
        
        token_usage = final_state.get('token_usage')
        extraction_cost = 0.0
        analysis_cost = 0.0
        total_cost = 0.0
        
        if token_usage:
            steps = token_usage.get("steps", {})
            extract_step = steps.get("extract", {})
            analyze_step = steps.get("analyze", {})
            
            if extract_step:
                extract_model = extract_step.get("model", "auto")
                extraction_cost = calculate_cost(extract_step, extract_model)
            
            if analyze_step:
                analyze_model = analyze_step.get("model", "auto")
                analysis_cost = calculate_cost(analyze_step, analyze_model)
            
            total_cost = extraction_cost + analysis_cost
        
        return {
            'symbol': symbol_upper,
            'status': 'complete',
            'final_report': final_state.get('final_report', ''),
            'state': final_state,
            'token_usage': token_usage,
            'extraction_cost': extraction_cost,
            'analysis_cost': analysis_cost,
            'total_cost': total_cost
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading result: {str(e)}")


@app.post("/api/llm-decision")
async def llm_decision(request: LLMDecisionRequest):
    """
    Get LLM decision combining user profile, technical analysis, and financial analysis.
    
    Args:
        request: Request with stock symbol and optional model preferences
        
    Returns:
        Decision with confidence, reasoning, and analysis
    """
    result = get_llm_decision(
        request.symbol,
        extraction_model=request.extraction_model,
        analysis_model=request.analysis_model,
        decision_model=request.decision_model
    )
    
    if result.get('status') == 'error':
        raise HTTPException(
            status_code=500,
            detail=result.get('error', 'Decision generation failed')
        )
    
    return result


@app.get("/api/analytics/summary")
async def get_analytics_summary(days: int = 7):
    """
    Get analytics summary for API usage.
    
    Args:
        days: Number of days to summarize (default: 7)
        
    Returns:
        Analytics summary with request counts, endpoints, errors, etc.
    """
    from utils import get_analytics_summary
    
    summary = get_analytics_summary(days=days)
    return summary


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)


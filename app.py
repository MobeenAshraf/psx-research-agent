"""FastAPI application for PSX Stock Analysis Frontend."""

import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from routes import get_technical_analysis, check_latest_report, run_financial_analysis
from state_monitor import stream_states, get_current_states


app = FastAPI(
    title="PSX Stock Analysis API",
    description="API for technical and financial analysis of PSX stocks",
    version="1.0.0"
)


static_dir = Path("static")
if static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import Response
    
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
    symbol: str


class FinancialAnalysisRequest(BaseModel):
    symbol: str
    pdf_text: Optional[str] = None
    pdf_url: Optional[str] = None


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
    result = check_latest_report(request.symbol)
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
        pdf_url=request.pdf_url
    )
    
    if result.get('status') == 'error':
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to start analysis'))
    
    return result


@app.get("/api/financial-analysis/stream/{symbol}")
async def stream_financial_analysis(symbol: str):
    """
    Stream financial analysis state updates via Server-Sent Events.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        SSE stream of state updates
    """
    async def event_generator():
        try:
            async for state_update in stream_states(symbol):
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
    symbol_upper = symbol.upper()
    states_dir = Path("data/results") / symbol_upper / "states"
    final_state_file = states_dir / "99_final_state.json"
    
    if not final_state_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Analysis not complete or not found"
        )
    
    try:
        with open(final_state_file, 'r', encoding='utf-8') as f:
            final_state = json.load(f)
        
        return {
            'symbol': symbol_upper,
            'status': 'complete',
            'final_report': final_state.get('final_report', ''),
            'state': final_state
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading result: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


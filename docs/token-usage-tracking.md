# Token Usage Tracking

## Current Status: ⚠️ PARTIALLY TRACKED

### Frontend (Google Analytics 4)

#### ✅ Financial Analysis - TRACKED
- **When:** Financial analysis completes successfully
- **What's tracked:** `total_tokens` (cumulative)
- **Event:** `analysis_completed`
```javascript
{
  analysis_type: 'financial',
  total_tokens: 5000  // Cumulative total from all steps
}
```

#### ❌ LLM Decision - NOT TRACKED
- Token usage is available in API response but not sent to GA4
- Should be added to `analysis_completed` event

#### ❌ Technical Analysis - NOT APPLICABLE
- Technical analysis doesn't use LLMs, so no token usage

### Backend (API Logging)

#### ❌ NOT TRACKED
- Token usage is **available** in API responses but **not logged**
- The infrastructure exists (`token_usage` parameter in `log_api_request`) but is always `None`
- Token usage data is not extracted from responses

---

## What Token Usage Data Is Available

### Financial Analysis Response
```json
{
  "token_usage": {
    "steps": {
      "extract": {
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "total_tokens": 1500
      },
      "analyze": {
        "prompt_tokens": 2000,
        "completion_tokens": 1000,
        "total_tokens": 3000
      }
    },
    "cumulative": {
      "prompt_tokens": 3000,
      "completion_tokens": 1500,
      "total_tokens": 4500
    }
  }
}
```

### LLM Decision Response
```json
{
  "token_usage": {
    "prompt_tokens": 2000,
    "completion_tokens": 800,
    "total_tokens": 2800
  }
}
```

---

## What We Should Track

### Frontend (GA4 Events)

#### Financial Analysis
✅ Currently tracked: `total_tokens` (cumulative)
- Could add: `prompt_tokens`, `completion_tokens`, `steps` breakdown

#### LLM Decision
❌ Should track: `total_tokens`, `prompt_tokens`, `completion_tokens`

### Backend (API Logs)

#### All Endpoints with Token Usage
❌ Should log:
- Endpoint: `/api/financial-analysis/run`
- Endpoint: `/api/financial-analysis/result/{symbol}`
- Endpoint: `/api/llm-decision`

Token usage should be extracted from response and logged.

---

## Implementation Gaps

### 1. Frontend - LLM Decision
**Location:** `static/app.js` line ~304
**Issue:** Token usage not included in `analysis_completed` event
**Fix:** Add token usage to event params

### 2. Backend - All Endpoints
**Location:** `app.py` AnalyticsMiddleware
**Issue:** Token usage not extracted from responses
**Fix:** Extract token_usage from response body and pass to `log_api_request`

### 3. Backend - Response Body Access
**Issue:** Middleware doesn't have access to response body
**Solution:** Use response interceptors or extract from endpoint responses

---

## Recommended Enhancements

### Option 1: Extract from Response in Endpoints
Add token usage to analytics in each endpoint:

```python
@app.post("/api/llm-decision")
async def llm_decision(request: LLMDecisionRequest):
    result = get_llm_decision(...)
    
    # Log with token usage
    if result.get('token_usage'):
        log_api_request(
            endpoint="/api/llm-decision",
            method="POST",
            status_code=200,
            duration_ms=duration,
            token_usage=result.get('token_usage')
        )
    
    return result
```

### Option 2: Response Interceptor Middleware
Create middleware that intercepts responses and extracts token_usage:

```python
class TokenUsageMiddleware:
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Extract token_usage from response if available
        if hasattr(response, 'body'):
            # Parse and extract token_usage
            pass
        
        return response
```

### Option 3: Custom Analytics Helper
Create helper function that endpoints call explicitly:

```python
from utils import track_analysis_with_tokens

@app.post("/api/llm-decision")
async def llm_decision(request: LLMDecisionRequest):
    start_time = time.time()
    result = get_llm_decision(...)
    duration = (time.time() - start_time) * 1000
    
    track_analysis_with_tokens(
        endpoint="/api/llm-decision",
        result=result,
        duration_ms=duration
    )
    
    return result
```

---

## Current Token Usage Display

### Frontend UI
✅ Token usage is **displayed** in the UI for:
- Financial Analysis results (detailed breakdown)
- LLM Decision results (simple display)

**Location:** `static/app.js` - `displayTokenUsage()` function

---

## Summary

| Component | Financial Analysis | LLM Decision | Technical Analysis |
|-----------|-------------------|---------------|-------------------|
| **Frontend (GA4)** | ✅ Tracked | ❌ Not tracked | N/A |
| **Backend (Logs)** | ❌ Not logged | ❌ Not logged | N/A |
| **UI Display** | ✅ Displayed | ✅ Displayed | N/A |

---

## Next Steps

1. **Add LLM Decision token tracking to GA4** (frontend)
2. **Extract token usage in backend middleware** (backend)
3. **Add token usage to analytics summary** (already supported, just needs data)

Would you like me to implement these enhancements?


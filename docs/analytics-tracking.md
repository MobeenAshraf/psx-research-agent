# Analytics Tracking - What We Track

## Overview

We track usage in two places:
1. **Frontend (Google Analytics 4)** - User interactions and events
2. **Backend (API Logging)** - API endpoint usage and performance

---

## Frontend Tracking (Google Analytics 4)

### Automatic Tracking
- **Page views** - Every time someone visits the site
- **User sessions** - ✅ Automatically tracked by GA4
  - Session starts: When user first interacts with site
  - Session ends: After 30 minutes of inactivity (default)
  - Session duration, pages per session
  - Engaged sessions (sessions > 10 seconds, 2+ page views, or conversion)
- **User demographics** - Location, device, browser (anonymized)
- **User identification** - Anonymous user IDs (via cookies)

### Custom Events

#### 1. `stock_symbol_entered`
**When:** User enters a stock symbol and presses Enter
```javascript
{
  stock_symbol: "SYS",
  method: "enter_key"
}
```

#### 2. `model_selected`
**When:** User changes extraction or analysis model
```javascript
{
  model_type: "extraction" | "analysis",
  model_name: "openai/gpt-4o" | "google/gemini-3-flash-preview"
}
```

#### 3. `analysis_started`
**When:** User clicks Technical, Financial, or LLM Decision button
```javascript
{
  analysis_type: "technical" | "financial" | "llm_decision",
  stock_symbol: "SYS",
  extraction_model: "google/gemini-3-flash-preview",  // (financial/llm only)
  analysis_model: "openai/gpt-4o"  // (financial/llm only)
}
```

#### 4. `analysis_completed`
**When:** Analysis finishes successfully
```javascript
{
  analysis_type: "technical" | "financial" | "llm_decision",
  stock_symbol: "SYS",
  duration_ms: 1234.56,
  success: true,
  cached: true,  // (financial only, if report existed)
  decision: "BUY" | "SELL" | "HOLD",  // (llm_decision only)
  confidence: 0.85,  // (llm_decision only)
  total_tokens: 5000  // (financial only, if available)
}
```

#### 5. `analysis_error`
**When:** Analysis fails or errors
```javascript
{
  analysis_type: "technical" | "financial" | "llm_decision",
  stock_symbol: "SYS",
  duration_ms: 500.23,
  error_message: "Analysis failed: Connection timeout"
}
```

---

## Backend Tracking (API Logging)

### What We Track

All API requests to `/api/*` endpoints are logged with:

#### Basic Request Info
- **timestamp** - ISO format UTC timestamp
- **endpoint** - Full endpoint path (e.g., `/api/technical-analysis`)
- **method** - HTTP method (GET, POST, etc.)
- **status_code** - HTTP response status (200, 404, 500, etc.)

#### Performance Metrics
- **duration_ms** - Request processing time in milliseconds

#### Error Tracking
- **error** - Error message if status_code >= 400

#### Request Data
- **request_data** - Currently empty `{}` (removed for performance)
  - Note: Can be enhanced to extract symbol from path params if needed

#### Token Usage (Future)
- **token_usage** - Currently `null`, can be populated from responses

### Example Log Entry

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "endpoint": "/api/technical-analysis",
  "method": "POST",
  "status_code": 200,
  "duration_ms": 1234.56,
  "request_data": {},
  "error": null,
  "token_usage": null
}
```

### Log Storage

- **Location:** `data/analytics/api_usage_YYYY-MM-DD.jsonl`
- **Format:** JSONL (one JSON object per line)
- **Rotation:** New file each day

---

## Analytics Summary Endpoint

### `/api/analytics/summary?days=7`

Returns aggregated statistics for the last N days:

```json
{
  "total_requests": 150,
  "endpoints": {
    "/api/technical-analysis": 50,
    "/api/financial-analysis/run": 30,
    "/api/llm-decision": 20,
    "/api/financial-analysis/check": 50
  },
  "status_codes": {
    "200": 140,
    "404": 5,
    "500": 5
  },
  "avg_duration_ms": 1234.56,
  "errors": 10,
  "token_usage": {
    "total_tokens": 500000,
    "total_requests_with_tokens": 50
  }
}
```

---

## What We DON'T Track

### Privacy-Conscious
- ❌ User IP addresses
- ❌ Personal information
- ❌ Request body content (removed for performance)
- ❌ Full error stack traces (only error messages)

### Performance-Conscious
- ❌ Request/response bodies (too large, would slow down)
- ❌ Headers (not needed for analytics)
- ❌ Full query strings (only endpoint path)

---

## How to View Analytics

### Google Analytics 4
1. Go to [Google Analytics](https://analytics.google.com)
2. Select your property (G-2ZELBC8870)
3. View:
   - **Realtime** - See events as they happen
   - **Events** - See all custom events
   - **Reports** - Standard GA4 reports

### Backend Analytics
1. **View logs:** Check `data/analytics/api_usage_*.jsonl` files
2. **Get summary:** `GET /api/analytics/summary?days=7`
3. **Query logs:** Use any JSONL reader or write custom scripts

---

## Key Metrics You Can Track

### User Behavior
- Which stock symbols are most popular
- Which analysis types are used most (Technical vs Financial vs LLM Decision)
- Model preferences (GPT vs Gemini)
- Analysis success/failure rates
- Average analysis duration

### API Performance
- Request volume by endpoint
- Average response times
- Error rates
- Peak usage times
- Token usage patterns (when available)

### Business Insights
- Most analyzed stocks
- User engagement patterns
- Feature usage (which models, which analysis types)
- Error patterns (which endpoints fail most)

---

## Privacy & Compliance

- ✅ No personal data collected
- ✅ No IP addresses logged
- ✅ Stock symbols are public data
- ✅ GA4 respects user privacy settings
- ✅ Backend logs are stored locally (your control)

---

## Future Enhancements

### Potential Additions
- [ ] Track token usage in backend logs (from API responses)
- [ ] Extract stock symbol from path params (e.g., `/api/result/SYS`)
- [ ] Add user agent tracking (device/browser info)
- [ ] Track analysis completion rates
- [ ] Add custom dimensions in GA4 for better segmentation


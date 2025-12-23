# Analytics Options Research

## Overview
This document outlines analytics options for tracking usage of the PSX Research Agent application, including both frontend interactions and backend API usage.

## Use Cases to Track

### Frontend Metrics
- Page views and unique visitors
- Stock symbol searches
- Analysis type selections (Technical, Financial, LLM Decision)
- Model selections (extraction/analysis models)
- User interactions and engagement

### Backend API Metrics
- API endpoint usage (technical-analysis, financial-analysis, llm-decision)
- Request frequency per endpoint
- Response times and performance
- Error rates
- Token usage patterns
- Model usage distribution

## Analytics Options

### 1. Google Analytics 4 (GA4)
**Pros:**
- Free and feature-rich
- Industry standard with extensive documentation
- Real-time data
- Integration with Google services (Ads, BigQuery)
- Event-based tracking model
- Custom events and dimensions
- Free tier with generous limits

**Cons:**
- Privacy concerns (GDPR, data ownership)
- Can be blocked by ad blockers
- Complex setup for advanced features
- Data stored on Google servers
- Requires cookie consent in many regions

**Best For:** Standard web analytics with Google ecosystem integration

**Implementation:** Add GA4 script to HTML, configure events for API calls

**Cost:** Free (GA4 360 enterprise: ~$50k/year)

---

### 2. Matomo (Self-Hosted)
**Pros:**
- Open-source and self-hostable (full data ownership)
- Privacy-compliant (GDPR, CCPA)
- No cookie consent required (when configured properly)
- Full control over data
- Real-time analytics
- Heatmaps and session recordings available
- Custom reports and dashboards
- API for custom integrations

**Cons:**
- Requires server resources for self-hosting
- More complex setup than cloud solutions
- Need to maintain and update

**Best For:** Privacy-focused organizations wanting full data control

**Implementation:** 
- Self-host Matomo instance
- Add tracking script to frontend
- Use Matomo API for backend tracking

**Cost:** Free (self-hosted) or $19-199/month (cloud)

---

### 3. Plausible Analytics
**Pros:**
- Lightweight and privacy-focused
- No cookies required (GDPR compliant)
- Simple, clean interface
- Open-source (can self-host)
- Fast loading (no performance impact)
- Bypasses ad blockers (when self-hosted)
- Easy to implement

**Cons:**
- Less feature-rich than GA4/Matomo
- Limited customization options
- Focused on page views (less event tracking)
- Self-hosted version requires maintenance

**Best For:** Simple, privacy-focused analytics without complexity

**Implementation:** Add lightweight script to HTML

**Cost:** $9-99/month (cloud) or Free (self-hosted)

---

### 4. Fathom Analytics
**Pros:**
- Privacy-focused (no cookies, GDPR compliant)
- Simple, intuitive interface
- Real-time data
- Unlimited data retention
- Bypasses ad blockers
- Fast and lightweight

**Cons:**
- Less feature-rich than Matomo
- Limited event tracking capabilities
- Paid service (no free tier)

**Best For:** Privacy-focused businesses wanting simplicity

**Cost:** $14-99/month

---

### 5. Custom Backend Analytics
**Pros:**
- Complete control over data
- Custom metrics specific to your needs
- No third-party dependencies
- Can track detailed API usage
- Privacy-compliant by design
- No additional costs

**Cons:**
- Requires development time
- Need to build dashboards/visualizations
- Storage and maintenance overhead
- No built-in features (heatmaps, etc.)

**Best For:** Specific metrics not available in standard tools

**Implementation:** 
- Add middleware to FastAPI to log requests
- Store in database (PostgreSQL, SQLite, or time-series DB)
- Build simple dashboard or use Grafana

**Cost:** Free (development time only)

---

### 6. Hybrid Approach
**Option A: Frontend Analytics + Backend Logging**
- Use Plausible/Matomo for frontend (page views, user interactions)
- Custom backend logging for API metrics (endpoints, performance, token usage)

**Option B: Full Custom Solution**
- Custom tracking for both frontend and backend
- Store in time-series database (InfluxDB, TimescaleDB)
- Use Grafana for visualization

---

## Recommendations

### For Quick Implementation (Recommended)
**Use: Plausible Analytics (Self-Hosted) + Custom Backend Logging**

**Why:**
1. **Plausible** provides simple, privacy-focused frontend analytics
2. **Custom backend logging** tracks detailed API metrics (endpoints, token usage, model selection)
3. Best balance of simplicity, privacy, and control
4. No ongoing costs (if self-hosting Plausible)

**Implementation Steps:**
1. Self-host Plausible (Docker container)
2. Add Plausible script to `templates/index.html`
3. Add FastAPI middleware to log API requests
4. Store API logs in database
5. Create simple dashboard for API metrics

### For Maximum Privacy
**Use: Matomo (Self-Hosted) + Custom Backend Logging**

**Why:**
1. Full data ownership
2. More features than Plausible
3. Better event tracking capabilities
4. Can track both frontend and backend via API

### For Standard Analytics
**Use: Google Analytics 4**

**Why:**
1. Free and feature-rich
2. Easy to implement
3. Industry standard
4. Good for general web analytics

**Note:** Consider privacy implications and cookie consent requirements

---

## Implementation Priority

### Phase 1: Basic Tracking (Week 1)
1. Add frontend analytics (Plausible or GA4)
2. Track page views and basic interactions
3. Track stock symbol searches

### Phase 2: API Tracking (Week 2)
1. Add FastAPI middleware for request logging
2. Track endpoint usage, response times, errors
3. Store in database

### Phase 3: Advanced Metrics (Week 3-4)
1. Track model selections
2. Track token usage patterns
3. Build dashboard for API metrics
4. Add custom events for user actions

---

## Technical Considerations

### Frontend Tracking
- Add analytics script to `templates/index.html`
- Track custom events for:
  - Stock symbol entered
  - Analysis type selected (Technical/Financial/LLM Decision)
  - Model selections
  - Analysis completion

### Backend Tracking
- FastAPI middleware to log:
  - Request path, method, status code
  - Response time
  - Request body (symbol, models)
  - Token usage (if available)
  - Error details

### Storage Options
- **SQLite**: Simple, good for small scale
- **PostgreSQL**: Better for production, supports JSON columns
- **InfluxDB/TimescaleDB**: Optimized for time-series data
- **File-based logs**: Simple but harder to query

---

## Privacy & Compliance

### GDPR Considerations
- If using GA4: Requires cookie consent banner
- If using Plausible/Matomo (no cookies): May not require consent
- Self-hosted solutions: Full control, easier compliance

### Data Retention
- Define retention policies
- Consider anonymization for long-term storage
- Regular cleanup of old data

---

## Implementation Status

### ✅ Completed (Google Analytics 4)

1. **Frontend Analytics (GA4)**
   - ✅ GA4 script added to `templates/index.html`
   - ✅ Custom event tracking for:
     - Stock symbol searches
     - Analysis type selections (Technical/Financial/LLM Decision)
     - Model selections (extraction/analysis models)
     - Analysis completions with duration and success status
     - Analysis errors with error messages
     - Token usage tracking

2. **Backend API Tracking**
   - ✅ FastAPI middleware for request logging
   - ✅ Tracks: endpoint, method, status code, duration, request data, errors
   - ✅ Logs stored in `data/analytics/api_usage_YYYY-MM-DD.jsonl`
   - ✅ Analytics summary endpoint: `/api/analytics/summary`

### 📋 Next Steps

1. **View Analytics**
   - Access GA4 dashboard at [Google Analytics](https://analytics.google.com)
   - View backend analytics via `/api/analytics/summary?days=7`

2. **Optional Enhancements**
   - Add token usage tracking to backend logs
   - Create simple dashboard for backend analytics
   - Set up automated reports
   - Add more custom dimensions in GA4

---

## Resources

- [Plausible Self-Hosting Guide](https://plausible.io/docs/self-hosting)
- [Matomo Installation Guide](https://matomo.org/docs/installation/)
- [Google Analytics 4 Setup](https://developers.google.com/analytics/devguides/collection/ga4)
- [FastAPI Middleware Documentation](https://fastapi.tiangolo.com/advanced/middleware/)


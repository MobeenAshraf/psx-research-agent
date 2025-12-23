# Session Tracking

## Current Status: ✅ YES - Sessions Are Tracked

### Google Analytics 4 (Automatic)

GA4 **automatically tracks sessions** with the basic implementation we have. No additional code needed.

#### What GA4 Tracks Automatically:
- ✅ **Session start** - When user first interacts with your site
- ✅ **Session end** - After 30 minutes of inactivity (configurable)
- ✅ **Session duration** - How long the session lasted
- ✅ **Pages per session** - Number of page views in the session
- ✅ **Engaged sessions** - Sessions that:
  - Last longer than 10 seconds, OR
  - Have 2+ page views, OR
  - Include a conversion event
- ✅ **Session ID** - Unique identifier for each session
- ✅ **User ID** - Anonymous identifier (via cookies)

#### Where to View Session Data:
1. **GA4 Dashboard** → Reports → Engagement → Overview
2. **Acquisition Reports** - See sessions by source/medium
3. **Realtime** - See active sessions right now

### Backend (Not Currently Tracked)

We do **NOT** track sessions in the backend API logs. Each API request is logged independently without session grouping.

---

## Session Details

### How GA4 Defines Sessions

**Session Start:**
- User first visits your site
- New session if previous session ended > 30 minutes ago
- New session if user arrives from a different campaign/source

**Session End:**
- 30 minutes of inactivity (default, configurable)
- User closes browser/tab
- New session starts (if user returns after 30+ minutes)

**Session Timeout:**
- Default: 30 minutes
- Can be changed in GA4 settings (0-4 hours)

### What You Can See in GA4

#### Session Metrics:
- **Total Sessions** - Number of sessions
- **Active Users** - Users with active sessions
- **Sessions per User** - Average sessions per user
- **Average Session Duration** - How long sessions last
- **Bounce Rate** - Single-page sessions
- **Engagement Rate** - Engaged sessions / total sessions

#### Session Dimensions:
- **Session Source** - Where users came from (direct, google, etc.)
- **Session Medium** - Type of traffic (organic, referral, etc.)
- **Session Campaign** - Campaign name (if applicable)
- **Device Category** - Desktop, mobile, tablet
- **Country/City** - Geographic location

---

## Custom Session Tracking (Optional)

### If You Want More Control

You can enhance session tracking with custom events:

#### 1. Track Session Start Explicitly
```javascript
// In app.js
trackEvent('session_start', {
  session_id: generateSessionId(),
  timestamp: new Date().toISOString()
});
```

#### 2. Track Session End
```javascript
// When user leaves
window.addEventListener('beforeunload', () => {
  trackEvent('session_end', {
    session_duration: calculateDuration(),
    pages_viewed: getPageViewCount()
  });
});
```

#### 3. Track User Journey Within Session
```javascript
// Track user flow
trackEvent('user_journey', {
  step: 'analysis_started',
  session_id: getSessionId(),
  previous_step: getPreviousStep()
});
```

### Backend Session Tracking (If Needed)

If you want to track sessions in backend logs:

```python
# Add session_id to log entries
log_entry = {
    "session_id": request.headers.get("X-Session-ID"),
    "user_id": request.headers.get("X-User-ID"),
    # ... other fields
}
```

---

## Current Implementation

### What We Have:
✅ **GA4 automatic session tracking** - Fully functional
- Sessions are automatically tracked
- Session metrics available in GA4 dashboard
- No code changes needed

### What We Don't Have:
❌ **Backend session tracking** - Not implemented
- API requests logged independently
- No session grouping in backend logs
- No session-based analytics in backend

---

## Recommendations

### For Most Use Cases:
**Current implementation is sufficient.** GA4 handles session tracking automatically and provides all standard session metrics.

### If You Need:
1. **Session-based API analytics** - Group API requests by session
2. **Custom session logic** - Different timeout rules, custom session IDs
3. **Backend session tracking** - Track sessions server-side

Then we can add custom session tracking.

---

## Viewing Session Data

### In Google Analytics 4:

1. **Realtime Sessions:**
   - GA4 Dashboard → Realtime
   - See active sessions right now

2. **Session Reports:**
   - Reports → Engagement → Overview
   - See total sessions, engaged sessions, session duration

3. **Session Breakdown:**
   - Reports → Acquisition → Traffic acquisition
   - See sessions by source, medium, campaign

4. **User Flow:**
   - Reports → Engagement → Path exploration
   - See how users navigate through sessions

### Example Queries:
- "How many sessions per day?"
- "What's the average session duration?"
- "Which sources drive the most sessions?"
- "How many engaged sessions do we have?"

---

## Summary

**Yes, sessions are tracked!** 

- ✅ GA4 automatically tracks all sessions
- ✅ No additional code needed
- ✅ Full session metrics available in GA4 dashboard
- ❌ Backend doesn't group requests by session (but could be added)

The current implementation gives you comprehensive session analytics through GA4. If you need session-based backend tracking, we can add that as an enhancement.


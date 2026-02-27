from datetime import datetime, timedelta
import re

def extract_time_filter(text):
    """
    Very small time parser that returns an Oracle WHERE fragment using sample_time column.
    Returns empty string if no time found.
    Examples handled:
     - "last 1 hour", "last one hour"
     - "last 10 minutes"
     - "yesterday 2am", "yesterday at 2am"
     - "at 02:00 yesterday"
    """
    t = text.lower()

    # last 1 hour
    if re.search(r"last\s+(1|one)\s+hour", t):
        past = datetime.now() - timedelta(hours=1)
        return f"AND sample_time > TO_TIMESTAMP('{past.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"

    # last N minutes (basic)
    m = re.search(r"last\s+(\d+)\s+minutes?", t)
    if m:
        mins = int(m.group(1))
        past = datetime.now() - timedelta(minutes=mins)
        return f"AND sample_time > TO_TIMESTAMP('{past.strftime('%Y-%m-%d %H:%M:%S')}', 'YYYY-MM-DD HH24:MI:SS')"

    # yesterday 2am or yesterday at 2am
    if "yesterday" in t:
        hm = re.search(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)?", t)
        if hm:
            hour = int(hm.group(1))
            minute = int(hm.group(2) or 0)
            ampm = hm.group(3)
            if ampm:
                if ampm == "pm" and hour != 12:
                    hour += 12
                if ampm == "am" and hour == 12:
                    hour = 0
        elif "2am" in t or "2 am" in t:
            hour, minute = 2, 0
        else:
            # default to midnight if no hour found
            hour, minute = 0, 0

        y = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return f"AND sample_time = TO_TIMESTAMP('{y} {hour:02d}:{minute:02d}:00', 'YYYY-MM-DD HH24:MI:SS')"

    return ""


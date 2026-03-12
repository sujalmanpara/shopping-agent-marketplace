def sse_event(event_type, data):
    return {"event": event_type, "data": data}
def sse_error(msg):
    return {"event": "error", "data": msg}

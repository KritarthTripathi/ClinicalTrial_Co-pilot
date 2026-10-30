def tag_span(**attrs):
    """Attach attributes (agent name, route, method) to the current Phoenix span. Silent if tracing is off."""
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        for k, v in attrs.items():
            span.set_attribute(k, str(v))
    except Exception:
        pass

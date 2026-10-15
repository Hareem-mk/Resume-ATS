"""Remove CrewAI-only cache metadata before a synchronous Groq LLM call."""
from functools import wraps


def clean_groq_messages(messages):
    """Copy message dictionaries without CrewAI's unsupported cache marker."""
    if not isinstance(messages, list):
        return messages
    return [
        {key: value for key, value in message.items() if key != 'cache_breakpoint'}
        if isinstance(message, dict) else message
        for message in messages
    ]


def apply_groq_compat(llm):
    """Wrap this LLM instance only; leave other sessions/providers untouched.

    Call immediately after constructing CrewAI's Groq LLM and before creating
    the agent. Quick mode uses llm.call(), the synchronous entry point.
    """
    if getattr(llm, '_mku_groq_cache_fixed', False):
        return llm
    original_call = llm.call

    @wraps(original_call)
    def call_without_cache_marker(messages, *args, **kwargs):
        return original_call(clean_groq_messages(messages), *args, **kwargs)

    llm.call = call_without_cache_marker
    llm._mku_groq_cache_fixed = True
    return llm

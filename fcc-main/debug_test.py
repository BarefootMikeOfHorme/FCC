#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from free_claude_code.core.output_schemas import VerbosityLevel, QueryResponse, OutputFormat
from free_claude_code.core.rich_output import RichOutputFormatter
from datetime import datetime, timezone

response = QueryResponse(
    response="Test",
    model_used="test",
    timestamp=datetime.now(timezone.utc).isoformat(),
    prompt_tokens=1,
    completion_tokens=1,
    total_tokens=2
)

formatter = RichOutputFormatter(VerbosityLevel.NORMAL)
result = formatter.format_query_response(response, OutputFormat.TEXT)
print(f"Type: {type(result)}")
print(f"Has __rich__: {hasattr(result, '__rich__')}")
print(f"Result: {result}")
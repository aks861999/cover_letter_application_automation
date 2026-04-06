import time
import logging


from pathlib import Path

from datetime import datetime
import re

def make_run_dir(base_output: Path, company_name: str) -> Path:
    """Create outputs/<company_name>_yyyy_mm_dd_hh_mm_ss/ and return the path."""
    safe_name = re.sub(r"[^\w\-]", "_", company_name.strip())  # sanitise for filesystem
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    run_dir = base_output / f"{safe_name}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir

logger = logging.getLogger(__name__)

# Errors worth retrying — transient server-side failures
_RETRYABLE = {"503", "429", "500", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "INTERNAL"}

# Wait times between attempts: 30s → 60s → 120s
_DELAYS = [30, 60, 120]
_MAX_RETRIES = 3

class MaxRetriesExceeded(Exception):
    """Raised when all retry attempts are exhausted. Stops the pipeline."""
    pass


def generate_with_retry(client, model: str, contents, config) -> object:
    """
    Drop-in wrapper for client.models.generate_content() with retry logic.
    Retries up to 3 times on transient errors (503, 429, 500).
    Raises immediately on non-retryable errors (400, 401, 403, etc.).
    """
    last_exc = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            err_str = str(exc)
            is_retryable = any(code in err_str for code in _RETRYABLE)

            if is_retryable and attempt < _MAX_RETRIES:
                delay = _DELAYS[attempt]
                logger.warning(
                    f"[Retry {attempt + 1}/{_MAX_RETRIES}] "
                    f"Transient error: {exc} — waiting {delay}s before retry..."
                )
                time.sleep(delay)
                last_exc = exc
            else:
                # Non-retryable or max retries exceeded — re-raise immediately
                raise

    raise MaxRetriesExceeded(
        f"API call failed after {_MAX_RETRIES} retries. Last error: {last_exc}"
    ) from last_exc
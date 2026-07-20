# [SPEC]
# Unit: src/llm_client-py/_retry_create.py
#
# _retry_create(client, model, messages) -> (str, dict)
#
# Pre-condition:
#   - client can send conversation messages for the given model and return text responses
#   - model is a non-empty string
#   - messages is a list of message dicts with "role" and "content" keys
#
# Post-condition:
#   - Returns a tuple of (response_text, usage_metadata_dict) from a successful LLM call
#   - response_text is the text content returned by the LLM
#   - usage_metadata_dict maps token-usage keys to numeric counts from the LLM response, or is an empty dict when no usage data is reported
#   - When the CLI backend is active, the LLM interaction is delegated to an external agent
#   - For direct client calls, Anthropic-family models use a dedicated native Anthropic endpoint; all other models use the standard chat-completions endpoint
#   - Recoverable errors (rate limiting, server unavailability, and other transient HTTP/middleware failures) are retried with increasing delay bounded by a per-category maximum retry count
#   - Non-recoverable errors (provider-rejected malformed requests) are propagated immediately without retry
#   - Raises RuntimeError when a recoverable error exhausts its retry budget
# [SPEC]

# [INFO]
# (no callees)
# [INFO]

def _retry_create(client, model, messages):
    """Call the LLM with retries. Returns (text, usage_dict).

    - Anthropic-family models go via the native /v1/messages endpoint.
    - Other models go through the OpenAI-compat client.
    - When LLM_API_BASE_URL matches INJECT_HOST, metadata.user_id is attached so
      third-party relays that support it can keep prompt-cache routing sticky.
    """
    if is_cli_backend_enabled():
        return run_agent_for_messages(model, messages)

    rate_limit_attempts = 0
    transient_attempts = 0
    use_anthropic = _is_anthropic_model(model)
    extra = {}
    if _should_inject_user_id(LLM_API_BASE_URL):
        extra["extra_body"] = _metadata_body()
    while True:
        try:
            if use_anthropic:
                return _anthropic_create(model, messages)
            response = client.chat.completions.create(model=model, messages=messages, **extra)
            text = response.choices[0].message.content
            usage = response.usage.model_dump() if response.usage else {}
            return text, usage
        except BadRequestError:
            raise
        except urllib.error.HTTPError as exc:
            status = exc.code
            body = _read_error_body(exc)  # the relay's raw error page (str(exc) drops it)
            detail = f"HTTP {status} {exc.reason}" + (f"; body={body!r}" if body else "")
            if status == 400:
                raise
            if status == 429:
                rate_limit_attempts += 1
                if rate_limit_attempts >= _MAX_RATE_LIMIT_RETRIES:
                    raise RuntimeError(
                        f"Rate limited after {_MAX_RATE_LIMIT_RETRIES} retries: {detail}"
                    ) from exc
                wait = min(2 ** (rate_limit_attempts - 1) * 5, 300) + random.uniform(1, 10)
                logging.warning(f"LLM 429 ({detail}), sleeping {wait:.1f}s (attempt {rate_limit_attempts})")
                time.sleep(wait)
                continue
            # 5xx and other → treat as transient
            transient_attempts += 1
            if transient_attempts >= _MAX_LLM_RETRIES:
                raise RuntimeError(
                    f"LLM request failed after {_MAX_LLM_RETRIES} retries: {detail}"
                ) from exc
            wait = min(2 ** (transient_attempts - 1) * 5, 60) + random.uniform(1, 3)
            logging.warning(f"LLM {detail}, sleeping {wait:.1f}s (attempt {transient_attempts})")
            time.sleep(wait)
        except RateLimitError as exc:
            rate_limit_attempts += 1
            if rate_limit_attempts >= _MAX_RATE_LIMIT_RETRIES:
                raise RuntimeError(
                    f"Rate limited after {_MAX_RATE_LIMIT_RETRIES} retries: {exc}"
                ) from exc
            wait = min(2 ** (rate_limit_attempts - 1) * 5, 300) + random.uniform(1, 10)
            logging.warning(f"LLM rate-limited, sleeping {wait:.1f}s (attempt {rate_limit_attempts})")
            time.sleep(wait)
        except Exception as exc:
            transient_attempts += 1
            if transient_attempts >= _MAX_LLM_RETRIES:
                raise RuntimeError(
                    f"LLM request failed after {_MAX_LLM_RETRIES} retries: {exc}"
                ) from exc
            wait = min(2 ** (transient_attempts - 1) * 5, 60) + random.uniform(1, 3)
            logging.warning(
                f"LLM error ({type(exc).__name__}: {str(exc)[:120]}), "
                f"sleeping {wait:.1f}s (attempt {transient_attempts})")
            time.sleep(wait)

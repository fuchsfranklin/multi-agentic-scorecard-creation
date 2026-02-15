"""
OpenRouter LLM client with rate limiting, retry logic, and daily usage tracking.

Supports both reasoning models (GPT-5 family, o3/o4-mini — no temperature/logprobs)
and standard models (GPT-4.1-mini, Gemini 3 Flash, Claude Sonnet 4) via OpenRouter's
OpenAI-compatible API.
"""
import os
import json
import time
import sys
import datetime
import threading
import requests

import config

API_KEY = config.OPENROUTER_API_KEY
API_HOST = config.OPENROUTER_API_HOST
HTTP_REFERER = config.HTTP_REFERER
X_TITLE = config.X_TITLE

# Models that don't support temperature or logprobs (reasoning models).
# GPT-5 family are all reasoning models with internal chain-of-thought.
_REASONING_MODELS = {
    "openai/o3-mini", "openai/o4-mini", "openai/o3", "openai/o3-pro",
    "openai/gpt-5", "openai/gpt-5-mini", "openai/gpt-5-nano",
    "openai/gpt-5.1", "openai/gpt-5.1-mini",
    "openai/gpt-5.2", "openai/gpt-5.2-chat",
}


class DailyRateLimitError(Exception):
    pass


# File to track usage (date, count, last_call timestamp)
USAGE_FILE = os.path.join(os.path.dirname(__file__), "llm_usage.json")
_usage_lock = threading.Lock()


def _load_usage():
    try:
        with open(USAGE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"date": datetime.date.today().isoformat(), "count": 0, "last_call": 0}


def _save_usage(usage):
    with open(USAGE_FILE, "w") as f:
        json.dump(usage, f)


class LLMClient:
    """OpenRouter chat-completions client with rate limiting and retries."""

    def __init__(self, model: str | None = None):
        self.model = model or config.PRIMARY_MODEL
        self.url = f"{API_HOST}/chat/completions"

    def generate(
        self,
        prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.0,
        max_retries: int = 3,
        expect_json: bool = False,
    ) -> str:
        """Send a single-turn prompt and return the assistant's text response."""
        # --- Throttle & daily limit ---
        with _usage_lock:
            usage = _load_usage()
            today = datetime.date.today().isoformat()
            if usage.get("date") != today:
                usage = {"date": today, "count": 0, "last_call": 0}
            if usage["count"] >= 200:
                raise DailyRateLimitError("Daily usage limit reached (200 calls)")
            now_ts = time.time()
            elapsed = now_ts - usage.get("last_call", 0)
            if elapsed < 2:
                wait = 2 - elapsed
                time.sleep(wait)
                now_ts = time.time()

        # --- Build request ---
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }
        if HTTP_REFERER:
            headers["HTTP-Referer"] = HTTP_REFERER
        if X_TITLE:
            headers["X-Title"] = X_TITLE

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }

        # Reasoning models don't support temperature
        is_reasoning = self.model in _REASONING_MODELS
        if not is_reasoning:
            payload["temperature"] = temperature

        if expect_json:
            payload["response_format"] = {"type": "json_object"}

        # --- Retry loop ---
        retries = max_retries
        last_exception = None
        while retries > 0:
            try:
                resp = requests.post(self.url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.HTTPError as e:
                last_exception = e
                if e.response.status_code == 429:
                    try:
                        error_data = e.response.json()
                        message = error_data.get("error", {}).get("message", "")
                        if "per-day" in message:
                            raise DailyRateLimitError(message) from e
                        elif "per-min" in message:
                            retries -= 1
                            print(f"Per-minute rate limit. Retrying in 65s... ({retries} left)", file=sys.stderr)
                            time.sleep(65)
                            continue
                        else:
                            raise e
                    except json.JSONDecodeError:
                        raise e
                else:
                    raise e
            except requests.RequestException as e:
                last_exception = e
                retries -= 1
                print(f"Network error: {e}. Retrying in 5s... ({retries} left)", file=sys.stderr)
                time.sleep(5)
                continue
        else:
            if last_exception:
                raise last_exception
            raise Exception("Failed to get response after retries.")

        # --- Update usage ---
        with _usage_lock:
            usage["count"] += 1
            usage["last_call"] = now_ts
            _save_usage(usage)

        # --- Parse response ---
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            print(f"Error extracting content: {e}", file=sys.stderr)
            print(json.dumps(data, indent=2), file=sys.stderr)
            return ""

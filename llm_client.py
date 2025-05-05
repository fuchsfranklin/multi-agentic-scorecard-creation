import os
import config
import requests
import json # Added for printing
import time # Added for sleep
import sys # Added for stderr printing

API_KEY = config.OPENROUTER_API_KEY
API_HOST = getattr(config, "OPENROUTER_API_HOST", "https://openrouter.ai/api/v1")
# Optional rank headers
HTTP_REFERER = getattr(config, "HTTP_REFERER", None)
X_TITLE = getattr(config, "X_TITLE", None)

# Custom exception for daily rate limit
class DailyRateLimitError(Exception):
    pass

class LLMClient:
    def __init__(self, model="deepseek/deepseek-v3-base:free"):  # Use DeepSeek V3 Base free model
        self.model = model
        self.url = f"{API_HOST}/chat/completions"

    def generate(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.0, max_retries: int = 3) -> str: # Increased max_tokens further
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
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        retries = max_retries
        last_exception = None
        while retries > 0:
            try:
                resp = requests.post(self.url, json=payload, headers=headers)
                resp.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                data = resp.json()
                # If successful, break the loop
                break
            except requests.HTTPError as e:
                last_exception = e
                if e.response.status_code == 429:
                    try:
                        error_data = e.response.json()
                        message = error_data.get("error", {}).get("message", "")
                        if "per-day" in message:
                            print(f"Daily rate limit hit: {message}", file=sys.stderr)
                            raise DailyRateLimitError(message) from e
                        elif "per-min" in message:
                            retries -= 1
                            wait_time = 65 # Wait 65 seconds
                            print(f"Per-minute rate limit hit. Retrying in {wait_time}s... ({retries} retries left)", file=sys.stderr)
                            time.sleep(wait_time)
                            continue # Retry the request
                        else:
                            # Unknown 429 error, treat as non-retryable
                            print(f"Unhandled 429 error: {message}", file=sys.stderr)
                            raise e
                    except json.JSONDecodeError:
                        # If the 429 response body isn't JSON, treat as non-retryable
                        print("Rate limit hit (429), but couldn't parse error response.", file=sys.stderr)
                        raise e
                else:
                    # Not a 429 error, re-raise immediately
                    raise e
            except requests.RequestException as e:
                # Handle other potential network errors
                last_exception = e
                retries -= 1
                print(f"Network error: {e}. Retrying in 5s... ({retries} retries left)", file=sys.stderr)
                time.sleep(5)
                continue

        # If the loop finished without breaking (i.e., all retries failed)
        else: # This else clause executes if the while loop completes normally (no break)
             if last_exception:
                 print(f"Max retries exceeded. Last error: {last_exception}", file=sys.stderr)
                 raise last_exception # Raise the last exception encountered
             else:
                 # Should not happen if loop runs at least once, but handle defensively
                 raise Exception("Failed to get response after retries, but no exception recorded.")


        # --- Response parsing ---
        try:
            # Attempt to extract the content as before
            content = data["choices"][0]["message"]["content"].strip()
            return content
        except (KeyError, IndexError, TypeError) as e:
            # If extraction fails on a successful response (should be rare with json_object format)
            print(f"Error extracting content from successful response: {e}")
            print("Raw API Response:")
            print(json.dumps(data, indent=2)) # Print the full JSON response
            # Return empty string or raise, depending on desired behavior for malformed success
            return "" # Return empty string on parsing error after success

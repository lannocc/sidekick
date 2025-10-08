# Proposal: Implementing Token Rate Limiting and Cooldowns

**Status**: Implemented

### Introduction

The IOSK system is currently experiencing `google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED` errors during periods of high activity. Analysis indicates this is primarily due to exceeding Google's tokens-per-minute (TPM) quota, which is set at 1 million TPM for most models. When this quota is hit, all subsequent requests to that model fail, causing AI agents to become unresponsive and disrupting user workflows. The current error handling in `src/iosk/chat.py` attempts to mitigate this by truncating session history, which is an incorrect response to a rate limit issue and can lead to context loss.

This proposal outlines a comprehensive strategy to manage and mitigate these rate limit errors. We will implement a robust system within the IOSK kernel that combines proactive TPM tracking with a reactive, device-specific cooldown mechanism. This will allow the system to gracefully handle API load, prevent hard failures, and automatically recover from rate-limiting events, ensuring greater stability and reliability for all AI agents.

### Core Concepts

1.  **Per-Device TPM Tracking**: The kernel will maintain a rolling 60-second count of tokens submitted for each specific AI model (device). This provides real-time visibility into our current usage against the known API quotas.

2.  **Proactive Throttling**: Before an AI trip is initiated, the system will perform a pre-flight check. If the new request is likely to push a device over its TPM quota, the request will be automatically and briefly delayed until sufficient capacity is available in the rolling window.

3.  **Reactive Cooldown**: When a `429` error is inevitably received, the system will parse the `retryDelay` suggested by the API, add a small safety buffer, and trigger a mandatory, system-wide cooldown *for that specific device only*. All other users and agents attempting to use the same device will be queued until the cooldown period expires.

4.  **Automatic Retry**: The original request that failed due to the rate limit will be automatically and transparently retried after the cooldown period. This ensures that from the user's or agent's perspective, the operation simply took longer to complete, rather than failing outright.

### Implementation Strategy

#### 1. Kernel Modifications (`src/iosk/kernel.py`)

The `IOSK` class will be augmented to act as the central manager for token rates and device availability.

*   **New Kernel Attributes**:
    *   `self.device_tpm_trackers`: A dictionary mapping device virtual paths to a list of `(timestamp, token_count)` tuples. This will track token usage for the rolling window.
    *   `self.device_cooldowns`: A dictionary mapping device virtual paths to an `asyncio.Event`. This event will be used to signal device availability. An event being *set* means the device is ready; *cleared* means it's in a cooldown period.

*   **Modify `log_trip_trace()` Method**:
    This method is already the perfect place to record token usage. It will be updated to:
    1.  Calculate the total tokens for the trip (prompt + reply).
    2.  Append `(datetime.now(), total_tokens)` to the list for the corresponding `io.dev` in `self.device_tpm_trackers`.

*   **New Kernel Methods**:
    *   **`_get_current_tpm(device_path)`**:
        *   This helper method will iterate through the tracker for the given `device_path`.
        *   It will prune all entries older than 60 seconds.
        *   It will return the sum of tokens for the remaining recent entries.

    *   **`async enforce_cooldown(device_path, delay_seconds)`**:
        *   Gets the `asyncio.Event` for the `device_path` from `self.device_cooldowns`, creating it if it doesn't exist.
        *   `event.clear()` to signal that the device is now unavailable.
        *   `await asyncio.sleep(delay_seconds)`.
        *   `event.set()` to signal that the device is ready again.

    *   **`async await_device_readiness(device_path, tokens_in_prompt)`**:
        *   This will be the new central entry point for all AI trips.
        *   It will first get the `asyncio.Event` for the `device_path` and call `await event.wait()` to ensure the device is not in a reactive cooldown.
        *   It will then call `_get_current_tpm()` and perform a proactive check. If `current_tpm + tokens_in_prompt` exceeds a threshold (e.g., 950,000), it will calculate the necessary `asyncio.sleep()` time for the oldest tokens in the window to expire, and wait.

#### 2. AI Trip Logic Modifications (`src/iosk/chat.py` and `bin/ask.py`)

The two main places that initiate AI trips must be updated to use the new kernel mechanisms.

*   **`src/iosk/chat.py` (`Engagement.engage`)**:
    The main `try...except` block will be significantly refactored.

    ```python
    # Conceptual change in Engagement.engage
    
    # ... prompt_text_for_trip is constructed ...
    
    # Pre-calculate prompt tokens for proactive check
    prompt_tokens = len(encoding.encode(prompt_text_for_trip))
    
    # Await readiness (proactive throttling and reactive cooldown wait)
    await self.io.os.await_device_readiness(self.io.dev, prompt_tokens)
    
    client = await self.io.os.get_device_client(self.io, self.io.dev)
    if not client:
        # ... handle client creation failure ...
        return

    for attempt in range(3): # Retry loop
        try:
            reply = await self.trip(client, prompt_text_for_trip)
            # Success, break the retry loop
            break 
        except ClientError as e:
            if "429" in str(e):
                # This is a rate limit error, handle it
                await self.io.print(":: API rate limit hit. Analyzing cooldown...")
                
                # Parse delay from error message
                match = re.search(r"'retryDelay': '(\d+)s'", str(e))
                delay = int(match.group(1)) + 2 if match else 15 # Default 15s
                
                await self.io.print(f":: Enforcing device cooldown for {delay} seconds.")
                
                # Trigger kernel to manage cooldown; this will block other users.
                # Run this as a background task so our retry loop can immediately wait on the event.
                asyncio.create_task(self.io.os.enforce_cooldown(self.io.dev, delay))

                # Now, wait for the cooldown to complete before retrying.
                await self.io.os.await_device_readiness(self.io.dev, 0)
                
                # Continue to the next attempt in the retry loop
                continue
            else:
                # Some other ClientError, fail fast
                await self.io.os.system.error(f'!! Unhandled Google ClientError for {self.io.user}: {e}')
                reply = None
                break
        except Exception as e:
            # Handle other exceptions
            # ...
            reply = None
            break

    # ... process the reply or failure ...
    ```

*   **`bin/ask.py`**:
    A similar `try...except` block with a retry loop will be added around the `google_trip` call to ensure the `ask` command also benefits from this resilience.

### Use Case Scenario

1.  Multiple agents (`alpha`, `beta`, `gamma`) are heavily using the `/dev/google/gemini-2.5-flash` device. The kernel's TPM tracker for this device shows usage at 900,000 tokens.
2.  Agent `delta` initiates a large `ask` command with a 60,000 token prompt. The `await_device_readiness` method sees that `900k + 60k > 950k`, so it proactively sleeps `delta`'s request for 3 seconds, waiting for older tokens to expire from the 60-second window.
3.  In that 3-second window, agent `alpha`'s request goes through, pushing the TPM over 1 million and triggering a `429` error.
4.  `alpha`'s `Engagement` handler catches the `ClientError` and parses a `9s` retry delay. It informs the user and calls `kernel.enforce_cooldown('/dev/google/gemini-2.5-flash', 11)`.
5.  The kernel immediately clears the `asyncio.Event` for that device, putting it into a "cooldown" state.
6.  `delta`'s request finishes its proactive sleep and now blocks on `await event.wait()` inside `await_device_readiness`, along with any new requests from other agents for the same device. Requests to other devices (e.g., `gpt-4o`) are unaffected.
7.  After 11 seconds, the kernel's `enforce_cooldown` task completes and `sets` the event.
8.  All waiting tasks (`delta`'s included) are unblocked. `alpha`'s failed request is automatically retried by its `Engagement` loop and now succeeds. The system has gracefully recovered.

### Benefits

*   **System Reliability**: Drastically reduces hard failures from API rate limits, making the entire system more stable and predictable.
*   **Agent Resilience**: Prevents AI agents from becoming "stuck" or unresponsive. Failed requests are handled transparently, improving the user experience.
*   **Efficient Resource Use**: Proactive throttling smooths out API traffic, making better use of the available quota and reducing the frequency of hitting hard limits.
*   **Centralized Control**: Manages rate limiting at the kernel level, ensuring consistent behavior across all parts of the system (`chat`, `ask`, future tools) without duplicating logic.

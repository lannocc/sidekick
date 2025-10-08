# Proposal: Per-Device Client Instance Management

**Status**: Implemented

### Introduction

The current implementation for LLM device interaction (e.g., in `src/iosk/dev/google.py` and `src/iosk/dev/openai.py`) utilizes a global, singleton client instance for each service. This client is initialized on first use and subsequently shared across all users and asynchronous operations targeting that service.

While functional for a simple setup, this singleton pattern is not robust or scalable. It prevents fine-grained configuration (such as per-user API keys or model-specific timeouts), introduces risks for future stateful interactions, and complicates testing.

This proposal outlines a plan to refactor the device layer by removing global client state. We will introduce a kernel-managed "device client factory" that creates, caches, and provides client instances on a per-device basis. This change will make the system more robust, flexible, and better aligned with modern software design principles.

### Rationale and Goals

The primary goal is to improve the architectural integrity and flexibility of the AI device interaction layer. The benefits of this change include:

*   **Configuration Flexibility**: By managing clients on a per-device basis, we can introduce device-specific configurations. This opens the door for future enhancements like using different API keys for different users/groups, setting custom timeouts for long-running models, or connecting to different API endpoints (e.g., for fine-tuned models).
*   **Robustness and Isolation**: It eliminates the risks associated with shared global state, ensuring that each device interaction is properly isolated and preventing potential context-mingling if client libraries were to introduce stateful features.
*   **Scalability**: Provides a clear pattern for managing resources. The kernel can control the lifecycle of client objects, allowing for more sophisticated strategies like connection pooling or client eviction if needed in the future.
*   **Improved Testability**: Individual components (like the `ask` command or a specific device module) can be tested in isolation by providing a mock client object, which is difficult to do with a hardcoded global instance.
*   **Code Clarity**: Removes the "magic" of a global variable, making the dependency on a client object explicit. Logic in `Engagement` and device modules becomes clearer about where the client comes from and how it is used.

### Proposed Implementation Strategy

The core of this proposal is to shift the responsibility of creating and managing client instances from the device modules themselves to the IOSK kernel, which will act as a central factory and cache.

#### 1. Kernel Modifications (`src/iosk/kernel.py`)

The `IOSK` class will be augmented to manage device clients.

*   **New Attribute**: Add a dictionary to `IOSK.__init__` to cache initialized clients:
    ```python
    self.device_clients = {}
    ```
*   **New Method**: Add a kernel method to get or create a client for a specific device.
    ```python
    async def get_device_client(self, io: 'Context', dev_virtual_path: str) -> object:
        """
        Gets a cached client instance for a device, or creates a new one.
        The client instance is cached using its virtual path as the key.
        """
        if dev_virtual_path in self.device_clients:
            return self.device_clients[dev_virtual_path]
    
        # Client not cached, so create it.
        # This requires a standardized way to get a client from a device module.
        dev_name = dev_virtual_path.replace('/dev/', '', 1)
        mod_name_for_pymod = dev_name.replace('/', '.')
        host_py_path = self.box(f"{dev_virtual_path}.py", io_context=io)
        dev_mod = self.pymod(f'dev.{mod_name_for_pymod}', host_py_path)
    
        if not dev_mod or not hasattr(dev_mod, 'get_client'):
            await io.error(f"!! device module for '{dev_virtual_path}' is invalid or missing get_client() function.")
            return None
    
        # Call the new standardized factory function in the device module.
        try:
            client = await dev_mod.get_client(io)
            if client:
                self.device_clients[dev_virtual_path] = client # Cache the new client
            return client
        except Exception as e:
            await io.error(f"!! failed to initialize client for '{dev_virtual_path}': {e}")
            return None
    ```

#### 2. Device Module Refactoring (e.g., `src/iosk/dev/google.py`)

All LLM device modules will be updated to conform to a new, stateless standard.

*   **Remove Global Client**: The `client = None` global variable will be removed.
*   **Standardize Client Creation**: The `online(io)` function will be replaced with a new factory function `async def get_client(io)`. This function is responsible for performing any one-time setup and returning a *new* client instance.
*   **Update `trip` Function Signature**: The `trip` function can no longer rely on a global client. It must accept the client instance as its first argument.

**Example: Changes for `src/iosk/dev/google.py`**
```python
# ./src/iosk/dev/google.py (New Version)

from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig

DEFAULT_MODEL = 'gemini-2.5-flash'
TIMEOUT = 3 * 60 * 1000

# NO global client variable here.

# New standardized factory function. Replaces online().
async def get_client(io):
    """Reads configuration and returns a new genai.Client instance."""
    api_key = (await io.os.get(io, '/etc/google')).strip()
    if not api_key:
        await io.error('!! google: no api key found in /etc/google')
        return None
    return genai.Client(api_key=api_key, http_options=HttpOptions(timeout=TIMEOUT))

# New trip function signature.
async def trip(client, prompt, model=DEFAULT_MODEL):
    """Performs a round trip using the provided client instance."""
    if not client:
        raise ValueError("Google client is not initialized.")
    resp = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=GenerateContentConfig(
            response_modalities=['TEXT'],
        ),
    )
    return resp.text

# iosend/iorecv/iosender remain mostly the same, but the 'trip' function
# they pass to the Engagement will need to be adapted.
# ... see Engagement changes below ...
```
Similar changes would be applied to `openai.py`, `ollama.py`, etc.

#### 3. `Engagement` Class Refactoring (`src/iosk/chat.py`)

The `Engagement.engage` method, which calls the `trip` function, must be updated to first retrieve the client from the kernel and then pass it to the `trip` function.

**Example: Changes for `Engagement.engage`**
```python
# ... inside the engage() loop, where a trip is about to happen ...

                # ... prompt_text_for_trip is constructed ...

                self.waiting = True
                reply = None
                try:
                    # 1. Get the client instance from the kernel for the user's current device.
                    client = await self.io.os.get_device_client(self.io, self.io.dev)

                    if client:
                        # 2. Call self.trip, passing the client as the first argument.
                        reply = await self.trip(client, prompt_text_for_trip)
                    else:
                        # Handle case where client could not be created.
                        # The error would have already been printed by get_device_client.
                        pass

                # ... rest of the exception handling and reply processing ...
```
To make this work, the `iosender` function in the device modules must be updated to pass the correct `trip` function reference to the engagement. Since the `Engagement` class now controls getting the client, the `iosender`'s `mtrip` wrapper is no longer necessary.

**Example: Changes for `google.py` `iosender` and `iosend`**
```python
# ... in src/iosk/dev/google.py ...

async def iosend(io, data):
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement: return
    # Pass a reference to the static trip function itself.
    engagement.append(data, trip)

async def iosender(io, data, model):
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement: return
    # The 'model' needs to be passed along. We can use a partial or lambda.
    # The engagement will provide the 'client' and 'prompt' arguments.
    model_specific_trip = lambda client, prompt: trip(client, prompt, model=model)
    engagement.append(data, model_specific_trip)

# ... iorecv remains the same ...
```

#### 4. `ask` Command Refactoring (`bin/ask.py`)

The `ask` command, which also calls `trip` functions directly, must undergo a similar change.

**Example: Changes for `bin/ask.py`**
```python
# ... inside ask.py's iocall, after determining the model and full_prompt ...

    # --- AI Interaction ---
    try:
        # 1. Determine the virtual device path for the selected model.
        # (This logic needs to be added, e.g., mapping model names to /dev/ paths)
        device_path = f"/dev/google/{model}" # Simplified example

        # 2. Get the client from the kernel.
        client = await io.os.get_device_client(io, device_path)
        if not client:
            # Error already printed, just exit.
            return False

        if not quiet_mode:
            await io.print(f":: asking {model} via {device_path}...")

        # 3. Call the trip function from the appropriate module, passing the client.
        response = await google_trip(client, prompt=full_prompt, model=model)

    # ... rest of the command ...
```

### Benefits in Practice

*   **Per-User Billing**: A future `get_client(io)` function could check `io.env` for a user-specific API key (e.g., `GOOGLE_API_KEY`). If present, it would use that key to initialize the client, allowing costs for that user's session to be tracked separately. If not present, it would fall back to the system key in `/etc/google`.
*   **Model-Specific Settings**: If we had a `gemini-2.5-pro-long-context` model that required a longer timeout, we could create a separate device file for it (`/dev/google/gemini-2.5-pro-long-context.py`). Its `get_client` function could initialize a client with a `timeout=1800` setting, while other models use the default. The kernel's client cache, being keyed by path, would manage both client instances correctly.

This proposal moves the IOSK system toward a more professional, robust, and extensible architecture for managing interactions with external AI services.


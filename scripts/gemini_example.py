import google.generativeai as genai
import os

# Configure the API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # Or replace with your actual API key.
if not GOOGLE_API_KEY:
    raise ValueError("Please set the GOOGLE_API_KEY environment variable.")

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize the generative model
#model = genai.GenerativeModel('gemini-pro')
model = genai.GenerativeModel('gemini-2.0-flash')

def generate_text(prompt):
    """
    Generates text using the Gemini Pro model.

    Args:
        prompt: The input text prompt.

    Returns:
        The generated text, or None if an error occurs.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def generate_text_with_safety_settings(prompt, safety_settings):
    """Generates text with custom safety settings."""
    try:
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def generate_text_with_stream(prompt):
    """Generates text and streams the output."""
    try:
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            print(chunk.text, end="") # Print each chunk as it arrives.
        print() #newline at the end.

    except Exception as e:
        print(f"An error occurred: {e}")
        return None



if __name__ == "__main__":
    #prompt = "Explain quantum computing in simple terms."
    prompt = "Write a simple python script."
    generated_text = generate_text(prompt)

    if generated_text:
        print("Generated Text:")
        print(generated_text)

    '''
    # Example of safety settings modification.
    safety_settings = [
        {
            "category": genai.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "threshold": genai.HarmBlockThreshold.BLOCK_NONE, # Allow all hate speech. (Use with extreme caution!)
        },
        {
            "category": genai.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "threshold": genai.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        },
        {
            "category": genai.HarmCategory.HARM_CATEGORY_HARASSMENT,
            "threshold": genai.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        {
            "category": genai.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            "threshold": genai.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
    ]

    prompt_unsafe = "Write a story that includes some hate speech." #Be extremely careful with this.
    unsafe_text = generate_text_with_safety_settings(prompt_unsafe, safety_settings)

    if unsafe_text:
        print("\nGenerated Unsafe Text (with modified safety settings):")
        print(unsafe_text)

    # Streaming example:

    stream_prompt = "Write a short poem about a cat."
    print("\nStreaming Poem:")
    generate_text_with_stream(stream_prompt)
    '''


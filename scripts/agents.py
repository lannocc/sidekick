import google.generativeai as genai
import os


PRE_PROMPT='''
Reply with a JSON list of maps where each map has values for these 2 keys:
    "agent" - name of the agent
    "prompt" - prompt for the agent

The available agents are:
    "file" - perform filesystem and git commands
    "browse" - interact with websites and capture the screen
    "wild" - catch-all for anything not understood or handled by the others
'''

META_PROMPT='''
Take the following prompt and select one or more agents from the list of available agents to handle the prompt or a section of it, in the appropriate sequential order.

PROMPT: 
'''

PROMPT='''
Take a screenshot of my Facebook friends list and save it to my home directory. Upload to imgr and delete it when finished.
'''

api_key = os.getenv('GEMINI_API_KEY')
assert api_key

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

prompt = PRE_PROMPT + META_PROMPT + PROMPT

resp = model.generate_content(prompt, stream=True)
for chunk in resp:
    print(chunk.text, end='')
print()


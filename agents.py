
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


# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from sk import ai


async def iosend(iosk, args):
    #print(f'GEMINI: {args}')
    return await ai.async_prompt_for_text(args)


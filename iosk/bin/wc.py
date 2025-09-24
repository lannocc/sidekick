import asyncio

async def iocall(io, argv):
    if not argv:
        await io.error('Usage: $ wc <filename>')
        return

    filename = argv[0]

    try:
        content = await io.os.get(io, filename)
        
        lines = content.count('\n') + (1 if content.strip() else 0)
        words = len(content.split())
        chars = len(content)

        await io.print(f"{lines}\t{words}\t{chars}\t{filename}")

    except FileNotFoundError:
        await io.error(f"wc: {filename}: No such file or directory")
    except Exception as e:
        await io.error(f"wc: Error processing {filename}: {e}")

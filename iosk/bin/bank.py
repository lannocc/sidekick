# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


async def iocall(io, args):
    args = args.split(' ')
    if len(args) != 2:
        await io.error('!! bank needs 2 arguments: <bank> <account>')
        return

    bank = args[0]
    acct = args[1]

    if not await io.os.exists(io, f'/bank/{bank}'):
        await io.error(f'!! bank does not exist: {bank}')
        return

    if not await io.os.exists(io, f'/bank/{bank}/{acct}'):
        await io.error(f'!! account does not exist: {acct}')
        return

    io.stage_bank(bank, acct)
    try:
        await io.os.exec(io, f'/bank/{bank}/{acct}')

    finally:
        io.stage_normal()


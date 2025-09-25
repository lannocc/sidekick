async def iocall(io, argv):
    if len(argv) != 2:
        await io.error('!! bank needs 2 arguments: <bank> <account>')
        return

    bank = argv[0]
    acct = argv[1]

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

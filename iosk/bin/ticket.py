import mysql.connector

async def iocall(io, argv):
    """View ticket details from the database.

    Usage: ticket <ticket-number>
           ticket --help

    <ticket-number>: The ID of the ticket to view (e.g., 123 or T123).
    --help:          Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not argv or len(argv) != 1:
        await io.error("!! ticket: ticket number required. Usage: ticket <ticket-number>")
        return False

    # --- Read configuration from /etc ---
    try:
        host = (await io.os.get(io, '/etc/ticket_db_host')).strip()
        user = (await io.os.get(io, '/etc/ticket_db_user')).strip()
        password = (await io.os.get(io, '/etc/ticket_db_pass')).strip()
        if not all([host, user, password]):
            await io.error("!! ticket: database configuration is incomplete in /etc/")
            return False
    except Exception as e:
        await io.error(f"!! ticket: could not read database configuration from /etc/: {e}")
        return False

    # --- Parse ticket number ---
    num_str = argv[0]
    if num_str.upper().startswith('T'):
        num_str = num_str[1:]

    try:
        task_id = int(num_str)
    except ValueError:
        await io.error(f"!! ticket: invalid ticket number format: {argv[0]}")
        return False

    # --- Connect to DB and fetch data ---
    db = None
    try:
        db = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database='phabricator_maniphest'
        )
        cur = db.cursor()

        # Fetch main ticket info
        sql_task = 'SELECT status, phid, description from maniphest_task WHERE id = %s'
        cur.execute(sql_task, (task_id,))
        ticket = cur.fetchone()

        if not ticket:
            await io.error(f'!! ticket: Ticket T{task_id} not found')
            return False

        ticket_status, ticket_phid, ticket_description = ticket

        # Fetch comments
        sql_comments = (
            'SELECT content '
            'FROM maniphest_transaction t '
            'LEFT JOIN maniphest_transaction_comment c '
            'ON c.phid = t.commentPHID '
            'WHERE t.objectPHID = %s and t.commentPHID is NOT NULL'
        )
        cur.execute(sql_comments, (ticket_phid,))
        comments = cur.fetchall()

        # --- Print formatted output ---
        await io.print(f'# Ticket T{task_id}')
        await io.print('')
        await io.print(f'- Status: **{ticket_status}**')
        await io.print('')
        await io.print('## Description')
        await io.print('')
        await io.print(ticket_description)

        if comments:
            await io.print('')
            await io.print('## Comments')
            line = False
            for comment in comments:
                await io.print('')
                if line:
                    await io.print('---')
                    await io.print('')
                await io.print(comment[0])
                line = True

    except mysql.connector.Error as err:
        await io.error(f"!! ticket: database error: {err}")
        return False
    except Exception as e:
        await io.error(f"!! ticket: an unexpected error occurred: {e}")
        return False
    finally:
        if db and db.is_connected():
            db.close()

    return True


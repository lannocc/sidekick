# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import config

import mysql.connector


def view(task_id:int):
    assert config.TICKET_DB_HOST
    assert config.TICKET_DB_USER
    assert task_id

    db = mysql.connector.connect(
            host=config.TICKET_DB_HOST,
            user=config.TICKET_DB_USER,
            password=config.TICKET_DB_PASS,
            database='phabricator_maniphest')

    cur = db.cursor()
    sql = 'SELECT status, phid, description from maniphest_task WHERE id = %s'
    cur.execute(sql, (task_id,))

    ticket = cur.fetchone()
    if not ticket:
        raise ValueError(f'Ticket T{task_id} not found')

    print(f'# Ticket T{task_id}')
    print()
    print(f'- Status: **{ticket[0]}**')
    #print(f'- PHID: {ticket[1]}')
    print()
    print('## Description')
    print()
    print(ticket[2])

    sql = 'SELECT content ' \
          'FROM maniphest_transaction t ' \
          'LEFT JOIN maniphest_transaction_comment c ' \
          '     ON c.phid = t.commentPHID ' \
          'WHERE t.objectPHID = %s and t.commentPHID is NOT NULL'
    cur.execute(sql, (ticket[1],))
    comments = cur.fetchall()

    if comments:
        print()
        print('## Comments')
        line = False

        for comment in comments:
            print()
            if line:
                print('---')
                print()
            print(comment[0])
            line = True


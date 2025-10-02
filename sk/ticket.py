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
    cur = db.cursor(buffered=True)

    sql = 'SELECT t.status, t.phid, t.description, tf.rawCorpus ' \
          'FROM maniphest_task t ' \
          'LEFT JOIN maniphest_task_ffield tf ON tf.documentID = t.id ' \
            " AND tf.fieldKey = 'titl' " \
          'WHERE t.id = %s'
    cur.execute(sql, (task_id,))

    ticket = cur.fetchone()
    if not ticket:
        raise ValueError(f'Ticket T{task_id} not found')

    phid = ticket[1]

    print(f'# Ticket T{task_id}: {ticket[3]}')
    print()
    print(f'- Status: **{ticket[0]}**')

    sql = 'SELECT content ' \
          'FROM maniphest_transaction t ' \
          'LEFT JOIN maniphest_transaction_comment c ' \
          '     ON c.phid = t.commentPHID ' \
          'WHERE t.objectPHID = %s and t.commentPHID is NOT NULL'
    cur.execute(sql, (phid,))
    comments = cur.fetchall()

    cur.close()
    db.close()

    db = mysql.connector.connect(
            host=config.TICKET_DB_HOST,
            user=config.TICKET_DB_USER,
            password=config.TICKET_DB_PASS,
            database='phabricator_project')
    cur = db.cursor(buffered=True)

    sql = 'SELECT p.name, pc.name ' \
          'FROM project_columnposition pcp ' \
          'LEFT JOIN project_column pc ON pc.phid = pcp.columnPHID ' \
          'LEFT JOIN project p ON p.phid = pc.projectPHID ' \
          'WHERE pcp.objectPHID = %s'
    cur.execute(sql, (phid,))
    board = cur.fetchone()

    if board:
        print(f'- Workboard: **{board[0]}**')
        print(f'- Column: **{board[1] or "(Backlog)"}**')

    else:
        print('- Workboard: **(None)**')
        print('- Column: **(None)**')

    print()
    print('## Description')
    print()
    print(ticket[2])

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

    cur.close()
    db.close()


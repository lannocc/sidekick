# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import config
from .util import print_flush, package_directory, take_screenshot

print = print_flush


def main(args, called=''):
    # All parsing happens in a single pass to allow mixing of options and arguments.
    use_openai = False
    quiet_flag_present = False
    chatter = False
    shot = False
    file = None
    pkg = []
    lang = None
    save = None
    save_work = None
    model_flag = None

    task = called.endswith('task')
    ask = not task and called.endswith('ask')

    remaining_args = []
    args_list = list(args)  # Create a mutable copy to pop from

    while args_list:
        arg = args_list.pop(0)

        if arg.startswith('-'):
            op = arg
            if op == '--help': op = '-h'
            if op == '--work': op = '-w'

            # If a command has already been seen, treat all subsequent options
            # as arguments for that command, not as global options.
            has_command = False
            for r_arg in remaining_args:
                if r_arg in COMMANDS:
                    has_command = True
                    break

            if has_command:
                remaining_args.append(arg)
                continue

            if op not in OPTIONS:
                # Handle unknown options
                if ask or task:
                    print(f'!!! unknown option: {op}')
                    return
                # For `sk` command, treat as part of the command/args
                remaining_args.append(op)
                continue

            ops = OPTIONS[op]

            # Handle options that cause an immediate exit
            if ops[0] is help or ops[0] is version:
                print(ops[1])
                ops[0](None)
                return

            # Handle options without arguments (flags)
            if op == '--openai': use_openai = True
            elif op == '-q': quiet_flag_present = True
            elif op == '-c': chatter = True
            elif op == '-s': shot = True
            elif op in ['-1', '-2', '-3']: model_flag = op

            # Handle options that take arguments
            elif op == '-a':
                if not args_list or args_list[0].startswith('-'):
                    print(f'!!! need a filename for -a')
                    return
                file = args_list.pop(0)
            elif op == '-e':
                if len(args_list) < 2 or args_list[0].startswith('-') or args_list[1].startswith('-'):
                    print(f'!!! -e needs 2 arguments: <language> <file>')
                    return
                lang = args_list.pop(0)
                save = args_list.pop(0)
            elif op == '-w':
                if not args_list or args_list[0].startswith('-'):
                    print(f'!!! need a filename for -w/--work')
                    return
                save_work = args_list.pop(0)

        else:  # Not an option, so it's a non-option argument
            remaining_args.append(arg)

    # --- Post-parsing setup ---
    if save and save_work:
        print('!!! -e and -w cannot be used together.')
        return

    quiet = quiet_flag_present or (remaining_args and remaining_args[0] == 'md')
    if not quiet: print('SIDEKICK: ', end='')

    # Set model based on flags
    if use_openai:
        if model_flag == '-1': model = config.OPENAI_MODEL_QUICK_1
        elif model_flag == '-3': model = config.OPENAI_MODEL_SMART
        else: model = config.OPENAI_MODEL_QUICK_2  # Default or -2
    else:
        if model_flag == '-1': model = config.GEMINI_MODEL_QUICK_1
        elif model_flag == '-3': model = config.GEMINI_MODEL_SMART
        else: model = config.GEMINI_MODEL_QUICK_2   # Default or -2


    # --- Mode Dispatch ---

    if task or ask:
        # For ask/task, all remaining non-option args are package paths
        pkg.extend(remaining_args)

        final_pkg = None
        if len(pkg) == 1:
            final_pkg = pkg[0]
        elif len(pkg) > 1:
            final_pkg = pkg

        prompt = None # Prompt is now handled interactively or via pipe
        if task:
            do_task(prompt, shot=shot, file=file, package=final_pkg, quiet=quiet,
                         chatter=chatter, model=model)
        else:
            ask_question(prompt, shot=shot, file=file, package=final_pkg,
                           mdlang=lang, mdsave=save, work_file=save_work, quiet=quiet,
                           chatter=chatter, model=model, use_openai=use_openai)
        return

    # command mode for `sk`
    args = remaining_args
    cmd = args[0] if args else None
    args = args[1:]

    if cmd not in COMMANDS:
        if cmd is None:
            print('!!! need an option or command')
        else:
            print(f'!!! unknown command: {cmd}')
        if not quiet: print('Try `sk help` for a list of commands.')
        return

    cmd_details = COMMANDS[cmd]
    if not quiet: print(cmd_details[1])
    cmd_details[0](args)


def ask_question(prompt=None, shot=False, file=None, package=None, mdlang=None,
                 mdsave=None, work_file=None, quiet=False, chatter=False,
                 model=config.GEMINI_MODEL_QUICK_2, use_openai=False):
    from .ai import google, openai
    from .util import get_md_code_block
    import sys

    if not quiet:
        print('Ask a Question')
        print()

    if shot or file or package:
        if sum([ 1 for item in [ shot, file, package ] if item ]) > 1:
            print('!!! only one of screenshot OR file OR package at a time !!!')
            return

        if shot:
            file, w, h = take_screenshot()
            if not quiet: print(f'SAVED SCREENSHOT to: {file}')

        elif package:
            file, counts = package_directory(package)
            if not quiet:
                print(f'PACKAGED DIRECTORY to: {file}')
                if isinstance(counts, list):
                    for i, c in enumerate(counts):
                        print(c)
                        print(package[i])
                else: print(counts)
                print()

    if (mdlang and not mdsave) or (mdsave and not mdlang):
        print('!!! need either both mdlang and mdsave, or neither')
        return

    # Changed: Get prompt from multi-line interactive input or pipe
    if sys.stdin.isatty():
        # Interactive mode
        if not quiet:
            print('    (Ctrl+D to finish)')
            print(' >> ', end='')
        prompt = sys.stdin.read()
    else:
        # Piped mode
        prompt = sys.stdin.read()

    if not prompt:
        return

    if not quiet:
        print()
        print("...waiting for reply...")

    ai_provider = openai if use_openai else google

    if file:
        answer = ai_provider.prompt_with_file_for_text(prompt, file, chatter=chatter,
                                              model=model)

    else:
        answer = ai_provider.prompt_for_text(prompt, chatter=chatter, model=model)

    summary = None
    answer_for_display = answer

    if work_file:
        from . import worker
        answer_for_display, summary = worker.do_work(prompt, answer, work_file)

    md = None
    if mdlang:
        md = get_md_code_block(mdlang or None, answer)
        if md: answer_for_display = answer.replace(md, '$$$ CODE EXTRACTED $$$')

    print()
    print(f' << {answer_for_display}')
    print()

    if mdsave:
        if md:
            with open(mdsave, 'w') as fout:
                fout.write(md)
                fout.write('\n')
            print(f':: SAVED {mdlang} TO {mdsave}')

        else:
            print(f'!! NO CODE TO SAVE')

    if summary:
        print(summary)
        print()


def do_task(prompt=None, shot=False, file=None, package=None, quiet=False,
            chatter=False, model=None):
    from . import agent
    from .action import Context
    from .util import play_error, play_success

    if not quiet:
        print('Perform a Task')
        print()

    if shot or file or package:
        if sum([ 1 for item in [ shot, file, package ] if item ]) > 1:
            print('!!! only one of screenshot OR file OR package at a time !!!')
            return

        if shot:
            file, w, h = take_screenshot()
            if not quiet: print(f'SAVED SCREENSHOT to: {file}')

        elif package:
            file, counts = package_directory(package)
            if not quiet:
                print(f'PACKAGED DIRECTORY to: {file}')
                if isinstance(counts, list):
                    for i, c in enumerate(counts):
                        print(c)
                        print(package[i])
                else: print(counts)
                print()

    if prompt:
        if not quiet: print(f' >> {prompt}')

    else:
        print(' >> ', end='')
        prompt = input()

    if not prompt:
        return

    if not quiet: print()
    context = Context(file)

    try:
        result = agent.just_do_it(context, prompt, quiet=quiet, chatter=chatter)

        if result is not None:
            play_success()
            return result

        else:
            play_error()
            return None

    except Exception as e:
        play_error()
        raise e


def help(args):
    print('AI SideKick')
    print()
    print('GENERAL USAGE:')
    #print('     sk [options] <command> [args...]')
    print('    ask [options] [directory-to-package ...]')
    print('   task [options] <command-prompt>')
    print()
    #print('Use `sk` for sidekick commands, `ask` questions, `task` for tasks.')
    print('Use `ask` to get a reply to a question or other prompt.')
    print('Use `task` to invoke our agents to do something useful.')
    print()
    print('The following general options are available:')
    for name, opt in OPTIONS.items():
        print(f'   {name} :: {opt[1]}')
    print()
    print('SEE ALSO:')
    print('     sk help')
    print('   iosk')


def version(args):
    from . import __version__
    print(f'Installed version is {__version__}')


def help_cmds(args):
    print('SideKick AI Admin')
    print()
    print('COMMAND USAGE:')
    print('     sk [options] <command> [args...]')
    print()
    print('Use `sk` to command and evaluate at a modular level.')
    print()
    print('The following commands are available:')
    for name, cmd in COMMANDS.items():
        print(f'   {name} :: {cmd[1]}')
    print()
    print('SEE ALSO:')
    print('    ask -h')
    print('   task -h')
    print('   iosk')


def agent(args):
    from .agent.cmd import main as agent_main

    agent_main(args)


def action(args):
    from .action.cmd import main as action_main

    action_main(args)


def ticket(args):
    from . import ticket

    if args:
        if len(args) != 1:
            print('1 argument required: <ticket-number>')
            return

        num = args[0]

    else:
        print('  >> Ticket Number: ', end='')
        num = input()
        if not num: return

        print('  <<')
        print()

    if num.upper().startswith('T'):
        num = num[1:]

    ticket.view(int(num))


def tree(args):
    from .util import get_directory_tree_as_text

    md = False
    count = False

    while args and args[0].startswith('-'):
        op = args[0]
        args = args[1:]

        if op == '-h' or op == '--help':
            print()
            print('COMMAND USAGE:')
            #print('     sk [options] <command> [args...]')
            print('    sk [general-opts] tree [tree-opts] <directory>')
            print()
            print('The following tree command options are available:')
            print('   -h  :: help for tree command (also --help)')
            print('   -md :: markdown compatible output')
            print('   -c  :: count bytes and tokens')
            print()
            print('See `sk -h` for general options.')
            return

        elif op == '-md':
            md = True

        elif op == '-c':
            count = True

        else:
            print(f'!!! unknown tree option: {op}')
            return

    if args:
        if len(args) != 1:
            print('1 argument required: <directory>')
            return

        path = args[0]

    else:
        print('  >> Directory: ', end='')
        path = input()
        if not path: return

        print('  <<')
        print()

    print(get_directory_tree_as_text(path, markdown=md, count=count))


def md(args):
    from .util import get_md_code_block
    import sys

    if args:
        if len(args) != 1:
            print('1 argument required: <language>')
            return

        lang = args[0]

    else:
        lang = None

    code = get_md_code_block(lang, sys.stdin.read())
    if code: print(code)


'''
def ask(args):
    from .ask.cmd import main as ask_main

    ask_main(args)
'''


def iosk(args):
    from .iosk.cmd import run as iosk_run

    iosk_run(args)


OPTIONS = {
    '-h': (help,
        'general help for sidekick (also --help)'),
    '-v': (version,
        'version information'),
    '-q': (None,
        'quiet operation (limited effect)'),
    '-c': (None,
        'print all chatter (even when quiet is enabled)'),
    '-s': (None,
        'take screenshot to use with prompt'),
    '-a': (None,
        'attach binary image/document with -a <filename>'),
    '-e': (None,
        '(ask only) extract a single markdown code block and save with -e <language> <file>'),
    '-w': (None,
        '(ask only) work on files, applying code blocks from reply, saves transcript to -w <file> (also --work)'),
    '--openai': (None,
        '(ask only) use OpenAI models instead of Google Gemini'),
    '-1': (None,
        '(ask only) use QUICK_1 model (gemini-2.0-flash / gpt-4o-mini)'),
    '-2': (None,
        '(ask only) use QUICK_2 model (gemini-2.5-flash / gpt-5-mini) [DEFAULT]'),
    '-3': (None,
        '(ask only) use SMART model (gemini-2.5-pro / gpt-5)'),
}


COMMANDS = {
    'help': (help_cmds,
        'help for sidekick commands'),
    'ver': (version,
        'version information'),
    'agent': (agent,
        'agents'),
    'action': (action,
        'actions'),
    'ticket': (ticket,
        'view ticket'),
    'tree': (tree,
        'print a directory tree'),
    'md': (md,
        'extract markdown code block'),
    #'ask': (ask,
    #    'ask commands'),
    'iosk': (iosk,
        'run iosk system'),
}


# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import config
from .util import print_flush, package_directory, take_screenshot
from .ask import ask_question
from .task import do_task

from binaryornot.check import is_binary
import tiktoken

import os
from datetime import datetime

print = print_flush


def _prepare_attachment(shot, file, package, quiet, use_openai=False):
    """Handles screenshot, file, and package attachments, ensuring only one is used."""
    attachment_content = ""
    final_file_path = file

    if sum([1 for item in [shot, file, package] if item]) > 1:
        print('!!! only one of screenshot OR file OR package at a time !!!')
        return None, None

    if shot:
        final_file_path, _, _ = take_screenshot() # w, h are unused
        if not quiet:
            print(f'SAVED SCREENSHOT to: {final_file_path}')

    elif package:
        final_file_path, counts = package_directory(package, use_openai=use_openai)
        if not quiet:
            print(f'PACKAGED to: {final_file_path}')
            if isinstance(counts, list):
                # Assuming counts has same length as package
                for i, count_str in enumerate(counts):
                    print(count_str)
                    print(package[i])
            else:
                print(counts)
            print()

    # After potential modification, check final_file_path
    if final_file_path and os.path.exists(final_file_path) and not is_binary(final_file_path):
        try:
            with open(final_file_path, 'r', encoding='utf-8') as f:
                attachment_content = f.read()
        except Exception as e:
            print(f"!!! could not read file {final_file_path}: {e}")
            return None, None

    return final_file_path, attachment_content


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
    work_flag = False
    model_flag = None

    task = called.endswith('task')
    ask = not task and called.endswith('ask')

    remaining_args = []
    args_list = list(args)  # Create a mutable copy to pop from

    # Short options that take an argument and thus cannot be combined.
    options_with_args = {'a', 'e'}

    while args_list:
        arg = args_list.pop(0)

        # Check for combined short options like -qcs, which don't take arguments.
        if arg.startswith('-') and not arg.startswith('--') and len(arg) > 2:
            chars = arg[1:]
            all_combinable = True
            for char in chars:
                if f'-{char}' not in OPTIONS or char in options_with_args:
                    all_combinable = False
                    break

            if all_combinable:
                # Expand the combined options into individual ones and prepend to the list.
                expanded_args = [f'-{char}' for char in chars]
                args_list[0:0] = expanded_args
                continue # Restart loop to process the first expanded option

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
            elif op in ['-1', '-2', '-3', '-4']: model_flag = op

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
                work_flag = True

        else:  # Not an option, so it's a non-option argument
            remaining_args.append(arg)

    # --- Post-parsing setup ---
    save_work = None
    if work_flag:
        import tempfile
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f'sidekick-work-{timestamp}.log'
        save_work = os.path.join(tempfile.gettempdir(), filename)
        # Print first thing, before any other output and before waiting for input.
        print(f':: Work transcript will be saved to: {save_work}')

        # We intentially open the transcript early and then append to it.
        # This way we still have a transcript if the program errors.
        with open(save_work, 'w', encoding='utf-8') as f:
            f.write("--- ARGUMENTS ---\n")
            f.write(' '.join([called] + list(args)))
            f.write("\n\n")

    if save and save_work:
        print('!!! -e and -w cannot be used together.')
        return

    quiet = quiet_flag_present or (remaining_args and remaining_args[0] == 'md')
    if not quiet: print('SIDEKICK: ', end='')

    # Set model based on flags
    if use_openai:
        if model_flag == '-1': model = config.OPENAI_MODEL_QUICK_1
        elif model_flag == '-3': model = config.OPENAI_MODEL_SMART_1
        elif model_flag == '-4': model = config.OPENAI_MODEL_SMART_2
        else: model = config.OPENAI_MODEL_QUICK_2  # Default or -2
    else:
        if model_flag == '-1': model = config.GEMINI_MODEL_QUICK_1
        elif model_flag == '-3': model = config.GEMINI_MODEL_SMART_1
        elif model_flag == '-4': model = config.GEMINI_MODEL_SMART_2
        else: model = config.GEMINI_MODEL_QUICK_2   # Default or -2


    # --- Mode Dispatch ---

    if task or ask:
        # For ask/task, all remaining non-option args are package paths (files or dirs)
        for path in remaining_args:
            if os.path.isfile(path):
                if is_binary(path):
                    print(f'!!! cannot package binary file specified as an argument: {path}')
                    return
                pkg.append(path)
            elif os.path.isdir(path):
                pkg.append(path)
            else:
                print(f'!!! path not found or is not a regular file/directory: {path}')
                return

        final_file_path, attachment_content = _prepare_attachment(shot, file, pkg or None, quiet, use_openai=use_openai)
        if final_file_path is None and attachment_content is None:
            # Error occurred and was printed in helper
            return

        prompt = None # Prompt is now handled interactively or via pipe
        if task:
            do_task(prompt, file=final_file_path, attachment_content=attachment_content, quiet=quiet,
                         chatter=chatter, model=model, use_openai=use_openai)
        else:
            ask_question(prompt, file=final_file_path, attachment_content=attachment_content,
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
    if args:
        sub_cmd = args[0]
        if sub_cmd in COMMANDS:
            cmd_handler = COMMANDS[sub_cmd][0]
            cmd_handler(['--help'])
            return
        else:
            print(f'!!! unknown command: {sub_cmd}')
            print('Try `sk help` for a list of commands.')
            return

    print('SideKick AI Admin')
    print()
    print('COMMAND USAGE:')
    print('     sk [options] <command> [args...]')
    print()
    print('Use `sk` to command and evaluate at a modular level.')
    print('For help on a specific command, use `sk help <command>`.')
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

    if args and (args[0] == '--help' or args[0] == '-h'):
        print("usage: sk ticket [<ticket-number>]")
        print("\nView ticket details. If no ticket number is provided, you will be prompted.")
        return

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
    use_openai = False

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
            print('   -h       :: help for tree command (also --help)')
            print('   -md      :: markdown compatible output')
            print('   -c       :: count bytes and tokens')
            print('   --google :: use google for token counting (default)')
            print('   --openai :: use openai (tiktoken) for token counting')
            print()
            print('See `sk -h` for general options.')
            return

        elif op == '-md':
            md = True

        elif op == '-c':
            count = True

        elif op == '--google':
            use_openai = False

        elif op == '--openai':
            use_openai = True

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

    print(get_directory_tree_as_text(path, markdown=md, count=count, use_openai=use_openai))


def md(args):
    from .util import get_md_code_block
    import sys

    if args and (args[0] == '--help' or args[0] == '-h'):
        print("usage: sk md [<language>]")
        print("\nExtract a markdown code block from stdin.")
        print("If language is not provided, it extracts the first code block found.")
        return

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


def local(args):
    from .local import main as local_main

    local_main(args)


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
        '(ask only) work on files, applying code blocks from reply, saves transcript to a temporary log file (also --work)'),
    '--openai': (None,
        '(ask only) use OpenAI models instead of Google Gemini'),
    '-1': (None,
        '(ask only) use QUICK_1 model (gemini-2.0-flash / gpt-4o-mini)'),
    '-2': (None,
        '(ask only) use QUICK_2 model (gemini-2.5-flash / gpt-5-mini) [DEFAULT]'),
    '-3': (None,
        '(ask only) use SMART_1 model (gemini-2.5-pro / gpt-5)'),
    '-4': (None,
        '(ask only) use SMART_2 model (gemini-3-pro-preview / gpt-5.1)'),
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
    'local': (local,
        'local backend service for SKYBOARD'),
}
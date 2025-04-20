# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import tempfile


class ActionsBase:
    def __init__(self, actions):
        self.to_do = [ ]

        for action in actions:
            name = action['action']
            del action['action']
            fn = getattr(self, 'do_' + name)
            self.to_do.append((name, fn, action))

    def do(self, context, quiet=False, chatter=False):
        for name, fn, args in self.to_do:
            if not quiet: print(f'        ** {name}( {args} )')
            result = fn(context, **args, quiet=quiet, chatter=chatter)

            if result is None:
                print(f'!!! action did not return a result !!!')
                return None

            if not isinstance(result, FileResult):
                fd, name = tempfile.mkstemp(prefix='sidekick-result-',
                                            suffix='.txt')

                with open(name, 'w', encoding='utf-8') as file:
                    file.write(result)

                if not quiet: print(f'SAVED RESULT to: {name}')
                result = FileResult(name)

            context.last_result = result

        return result


class Context:
    def __init__(self, file_path=None):
        self.last_agent = None
        self.last_result = FileResult(file_path) if file_path else None


class FileResult:
    def __init__(self, path_name):
        self.path_name = path_name


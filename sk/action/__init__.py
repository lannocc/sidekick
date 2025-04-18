# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


class ActionsBase:
    def __init__(self, actions):
        self.to_do = [ ]

        for action in actions:
            name = action['action']
            del action['action']
            fn = getattr(self, 'do_' + name)
            self.to_do.append((name, fn, action))

    def do(self):
        for name, fn, args in self.to_do:
            print(f'        ** {name}( {args} )')
            ok = fn(**args)
            if not ok:
                print(f'!!! action FAIL did not return True !!!')
                return False

        return True


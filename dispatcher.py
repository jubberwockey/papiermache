import warnings

class Dispatcher():

    def __init__(self, db_handler, commands):
        self.handler = db_handler
        self.commands = commands

    def verify_command(self, cmd_list):
        """checks if command follows structure of a valid command"""
        def recursive_verify(cmd_list, commands):
            if len(cmd_list) > 0:
                cmd = cmd_list.pop(0)
                if commands is not None:
                    if cmd in commands:
                        return recursive_verify(cmd_list, commands[cmd])
                    else:
                        warnings.warn('input not valid: {}'.format(cmd))
                        return False
                # collides with free-form input:
                else:
                    warnings.warn('too many inputs: {}'.format(cmd))
                    return False
            else:
                if commands is not None:
                    warnings.warn('additional input missing')
                    return False
                else:
                    return True
        # recursive_verify manipulates list, therefore copy:
        cmd_list_copy = list(cmd_list)
        return recursive_verify(cmd_list_copy, self.commands)

    def execute(self, input):
        cmd = input.split()
        if self.verify_command(cmd) is True:
            self.dispatch(cmd)

    def dispatch(self, cmd):
        execute_cmd = cmd.pop(0)

        if execute_cmd == 'find':
            self.execute_find(cmd)
        elif execute_cmd == 'select':
            self.execute_select(cmd)

    def execute_find(self, cmd_list):
        pass

    def execute_select(self, cmd_list):
        pass

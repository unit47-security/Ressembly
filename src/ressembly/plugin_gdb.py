"""Opt-in local annotations; no automatic hooks or plugin loading."""
import json
import gdb
from . import plugins, debug_gdb

_loaded = {}


class PluginCommand(gdb.Command):
    """rs-plugin list | inspect DIRECTORY | load DIRECTORY SHA256 | run ID | unload ID."""
    def __init__(self):
        super().__init__('rs-plugin', gdb.COMMAND_DATA)

    def invoke(self, argument, from_tty):
        self.dont_repeat()
        args = gdb.string_to_argv(argument)
        try:
            if args == ['list']:
                result = list(_loaded.values())
            elif len(args) == 2 and args[0] == 'inspect':
                result = plugins.describe(args[1])
            elif len(args) == 3 and args[0] == 'load':
                result = plugins.describe(args[1])
                plugins.require(result['sha256'] == args[2], 'hash mismatch')
                plugins.require(result['id'] not in _loaded, 'plugin id already loaded; unload first')
                _loaded[result['id']] = result
            elif len(args) == 2 and args[0] == 'run':
                plugins.require(args[1] in _loaded, 'plugin not loaded')
                item = _loaded[args[1]]
                result = plugins.run(item['path'], item['sha256'], debug_gdb.context_snapshot())
            elif len(args) == 2 and args[0] == 'unload':
                plugins.require(args[1] in _loaded, 'plugin not loaded')
                result = {'unloaded': _loaded.pop(args[1])['id']}
            else:
                raise ValueError('usage: rs-plugin list|inspect DIR|load DIR SHA256|run ID|unload ID')
            gdb.write(json.dumps(result, indent=2, ensure_ascii=True) + '\n')
        except (ValueError, OSError, KeyError, TypeError) as error:
            raise gdb.GdbError(str(error)) from error


def register():
    PluginCommand()

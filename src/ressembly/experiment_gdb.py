"""Persist a real selected-stop context without changing inferior execution."""
import gdb
from ressembly import debug_gdb, experiments


class Snapshot(gdb.Command):
    """rs-experiment-snapshot DOSSIER LABEL [ADDRESS LENGTH]: save stopped context."""
    def __init__(self):
        super().__init__('rs-experiment-snapshot', gdb.COMMAND_FILES)

    def invoke(self, argument, from_tty):
        self.dont_repeat()
        args = gdb.string_to_argv(argument)
        if len(args) not in (2, 4):
            raise gdb.GdbError('usage: rs-experiment-snapshot DOSSIER LABEL [ADDRESS LENGTH]')
        try:
            region = None
            if len(args) == 4:
                region = (int(args[2], 0), int(args[3], 0))
                debug_gdb.checked_range(region[0], region[1], 4096)
            snapshot = debug_gdb.context_snapshot()
            if region is not None:
                try:
                    snapshot['memory'] = debug_gdb.memory_dump(*region)
                except (ValueError, OSError, gdb.error) as error:
                    snapshot['memory'] = dict(address=region[0], length=region[1],
                                              status='unavailable', error=str(error))
                    snapshot['status'] = 'partial'
                    snapshot['errors']['memory'] = str(error)
            metadata = snapshot['metadata']
            identifier = experiments.add_snapshot(args[0], snapshot,
                metadata['executable_sha256'], metadata['run_id'], args[1], 'gdb_context')
            gdb.write('Saved snapshot ' + identifier + '\n')
        except (ValueError, OSError, TypeError, KeyError) as error:
            raise gdb.GdbError(str(error))


def register():
    Snapshot()

"""Small terminal entry point for the separately validated suite modules."""
import json
import gdb
from ressembly import labtools

HELP = '''Ressembly — Linux x86-64 laboratory suite
rs-context [--json]                      assembly, registers, stack, breakpoints
rs-maps                                 current mappings and permissions
rs-dump ADDRESS LENGTH                  at most 4096 bytes
rs-search ADDRESS LENGTH HEXBYTES        at most 65536 bytes
rs-chain ADDRESS DEPTH                  at most 32 pointers
rs-heap-view [arena [LIMIT]|chunk ADDRESS] [--json]
rsheap-start FILE [LIMIT]                selected malloc/free history (glibc 2.36 / 2.43)
rsheap-continue / rsheap-watch OBJECT_ID OFFSET WIDTH / rsheap-show / rsheap-stop
rs-lab pattern LENGTH WIDTH             bounded cyclic bytes displayed as hex
rs-lab offset HEXBYTES LENGTH WIDTH      offset candidates, never silent truncation
rs-lab elf FILE                         static ELF properties, not exploitability
rs-experiment-snapshot FILE LABEL [ADDRESS LENGTH]
rshist-start FILE [LIMIT] / continue / watch OBJECT OFFSET WIDTH / show / stop
  Extended history: calloc/realloc and up to four regions; separate from rsheap capture.
rs-plugin inspect DIR / load DIR SHA256 / run ID / unload ID
rs-code-reference NEW_FILE [ADDRESS]     verified local Ghidra code link
Persistent dossier creation, input, notes, comparison, export:
  python3 scripts/ressembly-experiment.py --help
Only declared single-process/single-thread profiles are supported.
'''

class Help(gdb.Command):
    """Show Ressembly commands and scope."""
    def __init__(self):
        super().__init__('rs-help', gdb.COMMAND_SUPPORT)

    def invoke(self, argument, from_tty):
        if argument.strip():
            raise gdb.GdbError('usage: rs-help')
        gdb.write(HELP)

class Lab(gdb.Command):
    """rs-lab pattern LENGTH WIDTH | offset HEXBYTES LENGTH WIDTH | elf FILE."""
    def __init__(self):
        super().__init__('rs-lab', gdb.COMMAND_DATA)

    def invoke(self, argument, from_tty):
        self.dont_repeat()
        args = gdb.string_to_argv(argument)
        try:
            if len(args) == 3 and args[0] == 'pattern':
                result = {'hex': labtools.cyclic(int(args[1], 0), int(args[2], 0)).hex(),
                          'width': int(args[2], 0)}
            elif len(args) == 4 and args[0] == 'offset':
                result = labtools.cyclic_offset(bytes.fromhex(args[1]), int(args[2], 0), int(args[3], 0))
            elif len(args) == 2 and args[0] == 'elf':
                result = labtools.elf_properties(args[1])
            else:
                raise ValueError('usage: rs-lab pattern LENGTH WIDTH | offset HEXBYTES LENGTH WIDTH | elf FILE')
            gdb.write(json.dumps(result, indent=2, ensure_ascii=True) + '\n')
        except (ValueError, OSError) as error:
            raise gdb.GdbError(str(error)) from error

def register():
    Help()
    Lab()

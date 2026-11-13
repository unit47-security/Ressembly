"""Load Ressembly read-only context and memory commands into GDB."""
import os
import sys
import gdb
if getattr(gdb, '_ressembly_debug_loaded', False):
    raise gdb.GdbError('Ressembly debug commands are already loaded')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ressembly import debug_gdb
_debug_registration = debug_gdb.register()
gdb._ressembly_debug_loaded = True

"""GDB loader. Session state lives in an imported module, never source globals."""
import os
import sys
import gdb
if getattr(gdb, '_ressembly_marker_loaded', False):
    raise gdb.GdbError('Use a fresh GDB session; marker collector is already loaded')
if getattr(gdb, '_ressembly_heap_loaded', False):
    raise gdb.GdbError('Ressembly heap collector is already loaded')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ressembly import heap_gdb
heap_gdb.register()
gdb._ressembly_heap_loaded = True

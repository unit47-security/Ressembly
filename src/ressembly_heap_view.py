"""GDB loader for a read-only glibc structural view, independent of collection."""
import os
import sys
import gdb
if getattr(gdb, '_ressembly_heap_view_loaded', False):
    raise gdb.GdbError('Ressembly heap view is already loaded')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ressembly import heap_view_gdb
heap_view_gdb.register()
gdb._ressembly_heap_view_loaded = True

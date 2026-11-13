"""Load opt-in extended history; use a fresh GDB session separate from v1 capture."""
import os
import sys
import gdb
if getattr(gdb,'_ressembly_history_loaded',False):
    raise gdb.GdbError('extended history already loaded')
if getattr(gdb,'_ressembly_marker_loaded',False):
    raise gdb.GdbError('use a fresh GDB session separate from marker acquisition')
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from ressembly import history_v2_gdb
history_v2_gdb.register()
gdb._ressembly_history_loaded=True

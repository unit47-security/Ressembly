"""GDB loader for persistent selected-stop snapshots."""
import os
import sys
import gdb

if getattr(gdb, '_ressembly_experiment_loaded', False):
    raise gdb.GdbError('Ressembly experiment commands already loaded')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ressembly import experiment_gdb
experiment_gdb.register()
gdb._ressembly_experiment_loaded = True

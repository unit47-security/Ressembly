"""Load the terminal modules; original marker experiment remains separate."""
import os
import sys
import gdb

if getattr(gdb, '_ressembly_marker_loaded', False):
    raise gdb.GdbError('Use a fresh GDB session; the historical marker adapter is loaded')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ressembly import debug_gdb, heap_gdb, heap_view_gdb, experiment_gdb, suite_gdb, plugin_gdb, reference_gdb, history_v2_gdb

for _rs_module, _rs_flag in (
        (debug_gdb, '_ressembly_debug_loaded'),
        (heap_gdb, '_ressembly_heap_loaded'),
        (heap_view_gdb, '_ressembly_heap_view_loaded'),
        (experiment_gdb, '_ressembly_experiment_loaded'),
        (history_v2_gdb, '_ressembly_history_loaded'),
        (plugin_gdb, '_ressembly_plugins_loaded'),
        (reference_gdb, '_ressembly_reference_loaded'),
        (suite_gdb, '_ressembly_suite_loaded')):
    if not getattr(gdb, _rs_flag, False):
        _rs_module.register()
        setattr(gdb, _rs_flag, True)
gdb.write('Ressembly loaded. Use rs-help for commands and supported scope.\n')

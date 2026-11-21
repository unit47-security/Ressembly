# Practical trial of the local alpha

This historical walkthrough used the pilot package already checked in the Debian x86-64 lab. The trial installation was separate from development experiments. Automated validation and user experience are recorded separately. During the trial, note any unclear instructions.

With the Debian VM running, open Terminal on the Mac:

```sh
cd /Users/user/Documents/ChatGPT/Ressembly
sh work/linux-lab/ssh-lab.sh -t '/home/lab/ressembly-user-trial/bin/ressembly gdb /home/lab/ressembly-user-work/debug_lab'
```

At the GDB prompt, enter one command at a time:

```gdb
set pagination off
break debug_stop
run
rs-context
rs-maps
rs-help
quit
```

When quitting, confirm closure of the fixture if GDB prompts you. Check whether you can start the debugger from the guide, read assembly, registers, and stack, and find the available commands without help. Share the outcome and any unclear steps. The trial concerns usability.

The pilot predates the final R4/R5 archive. Technical checks on the final package are separate from the human walkthrough. If a user trial is postponed, the report records that it was not run.

## Recorded outcome

The user reported “everything worked, great” after testing context, maps, and help. Pasting several lines at once caused initial difficulty. Entering **one command at a time** resolved it. The result is recorded in `work/r4-r5-gates/user-trial.json`. This is user confirmation of the tested path. It provides no independent performance measurement or validation of every module. After the authorized VM removal, the SSH command became a historical reference. Rebuild the lab to repeat the trial.

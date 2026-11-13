# Confronto corrente — 24 ottobre 2026

Ricognizione di fonti primarie online; nessun benchmark o bug dei concorrenti riprodotto. Le pagine stable/current sono mobili: versioni effettive e compatibilità devono essere fissate nel prossimo laboratorio. Nessuna rivendicazione di novità, superiorità o domanda di mercato validata.

| Strumento | Capacità documentate | Limiti pertinenti |
|---|---|---|
| GEF | Contesto registri/stack/codice, mappe, ricerca, heap glibc; helper che segue allocazioni e liberazioni e segnala possibili anomalie. | L'helper è dichiarato instabile, con falsi positivi e casi mancati. Non equivale a tutte le scritture. |
| Pwndbg | Contesto, mappe, telescope, heap glibc, cyclic/checksec; `track-heap` con attribuzione al chiamante, indirizzi relativi e breakpoint hardware. | La pagina operativa elenca UAF rilevabile; non attribuiamo altri rilevamenti senza prova. Non presumere supporto di ogni libc/allocator. |
| GDB | Breakpoint e memoria via Python, watchpoint, record/replay e reverse execution. | `watch` segnala cambi di valore, può perdere scritture dello stesso valore; numero e dimensioni hardware limitati, fallback software costoso. `btrace` non registra dati memoria. |
| rr | Record/replay Linux con GDB e reverse watchpoint. | Vincoli CPU/kernel/syscall; emula un core; memoria condivisa con processi esterni all'albero non supportata. |
| Tenet | Esplorazione di tracce x86/AMD64 in IDA, timeline, ricerca letture/scritture. | È un lettore, non un recorder; copertura dipende dalla traccia, accessi esterni/kernel possono mancare. |

Fonti primarie consultate:

- GEF: [context](https://hugsy.github.io/gef/commands/context/), [vmmap](https://hugsy.github.io/gef/commands/vmmap/), [search-pattern](https://hugsy.github.io/gef/commands/search-pattern/), [heap](https://hugsy.github.io/gef/commands/heap/), [heap-analysis-helper](https://hugsy.github.io/gef/commands/heap-analysis-helper/).
- Pwndbg: [catalogo](https://pwndbg.re/stable/commands/), [track-heap](https://pwndbg.re/stable/commands/linux_libc_elf/track-heap/), [release upstream](https://github.com/pwndbg/pwndbg/releases).
- GDB: [watchpoint](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Watchpoints.html), [record/replay](https://www.sourceware.org/gdb/download/onlinedocs/gdb.html/Process-Record-and-Replay.html), [Python breakpoint](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Breakpoints-In-Python.html), [lettura memoria](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Inferiors-In-Python.html).
- [rr ufficiale](https://rr-project.org/) e [Tenet upstream](https://github.com/gaasedelen/tenet).

## Implicazioni

La cronologia degli oggetti, i watchpoint e la timeline non sono nuovi in quanto tali. L'ipotesi da misurare è l'utilità di un flusso coerente con identità per generazione, riferimenti alle evidenze e limiti chiari. I moduli exploit-lab e heap devono confrontarsi con capacità già disponibili. Nessuna integrazione con questi strumenti è già implementata.

## Confronto sperimentale ancora aperto (R0)

Tre programmi nostri: scrittura oltre buffer, uso dopo liberazione, sovrascrittura puntatore, ciascuno con controllo senza errore. In laboratorio Linux autorizzato fissare hash, compilatore, glibc, GDB, revisioni GEF/Pwndbg, comandi e ordine dei compiti; conservare log e osservazioni manuali. Misurare passaggi, tempi, eventi mancanti ed errori di interpretazione con ripetizioni. Non chiamare bug l'assenza di una funzione non promessa. Questo audit non ha eseguito tali prove.

## Riferimenti storici

Il precedente confronto Windows includeva [x64dbg Trace](https://help.x64dbg.com/en/latest/gui/views/Trace.html), [Lighthouse](https://github.com/gaasedelen/lighthouse), [Dragon Dance](https://github.com/0ffffffffh/dragondance), [WinDbg TTD](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/time-travel-debugging-overview) e [Pernosco](https://pernos.co/). Restano riferimenti storici, non un piano Windows corrente né nuove verifiche sperimentali.

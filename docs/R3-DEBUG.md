# R3a/R3b — contesto debugger ed esplorazione memoria

Implementazione locale per GDB Python, Linux x86-64, connessione nativa locale e un solo thread fermo. Nessuna dipendenza da GEF/Pwndbg. Il laboratorio di convalida è Debian 12 x86-64 con GDB 13.1 in QEMU TCG sul Mac ARM64: non attesta Kali o prestazioni native.

## Uso

Da una nuova sessione `gdb -nx`, caricare il proprio programma, impostare un breakpoint e avviarlo; quando è fermo:

```gdb
source /percorso/Ressembly/src/ressembly_debug.py
rs-context
rs-context --json
rs-maps
rs-dump 0xINDIRIZZO 64
rs-search 0xINDIRIZZO 4096 616263
rs-chain 0xINDIRIZZO 8
```

Gli indirizzi sono numeri decimali o esadecimali: sostituire `0xINDIRIZZO` con un numero reale. I comandi non valutano espressioni C, chiamate a funzioni o assegnamenti; ricavare prima un indirizzo con i normali comandi di GDB. La vista contesto usa sempre il frame più recente del thread selezionato, senza cambiare frame o thread scelti dall'utente. Assembly: otto istruzioni **in avanti dal PC corrente**; registri generali AMD64 ed EFLAGS; stack: otto parole da RSP; breakpoint: numero, tipo, posizione dichiarata, abilitazione, pending, temporaneità, conteggio arresti. Non è una ricostruzione del call stack o delle istruzioni precedenti al PC.

## API e provenienza

`ressembly.debug_gdb.context_snapshot()` restituisce un dizionario JSON `ressembly.debug-context.v1`. Ogni chiamata assegna un nuovo `snapshot_id`; `metadata.run_id` combina identificativo del boot Linux, PID e tick di creazione del processo. `metadata.executable_sha256` è calcolato sull'eseguibile realmente aperto attraverso `/proc/PID/exe`, non solo sul percorso dichiarato. GDB, architettura, PID, thread, sistema operativo e impostazione degli argomenti sono registrati. Gli argomenti GDB rappresentano configurazione dichiarata, **non prova di input consumato**.

Gli errori di lettura dei registri, assembly o stack sono espliciti in `errors`; la vista diventa `partial`. Dopo l'uscita o senza processo attivo la richiesta è rifiutata: nessun riuso silenzioso dell'ultimo snapshot. I registri/frame sono riletti ad ogni chiamata. Nessun callback modifica l'esecuzione. Non sono tracciate scritture o accessi intermedi.

## Limiti misurabili

- Mappe: `/proc/PID/maps` corrente, tetto 2 MiB di testo; lettura eseguibile per hash massimo 256 MiB.
- Dump: 1–4096 byte; intervallo interamente mappato e leggibile. Le pagine senza permesso `r` sono rifiutate anche quando ptrace consentirebbe una lettura.
- Ricerca: intervallo esplicito 1–65536 byte, pattern esadecimale 1–256 byte, massimo 256 risultati; include corrispondenze sovrapposte. Si ferma al primo tratto non leggibile e lo dichiara. `bytes_read` misura il prefisso letto; `scanned_bytes` è ignoto (`null`) quando il limite risultati interrompe la ricerca. Non cerca automaticamente tutta la memoria del processo.
- Puntatori: parole little-endian di 8 byte, profondità 1–32. Fine esplicita `null`, `cycle`, `depth_limit`, `unreadable`. Il valore è interpretato come indirizzo, senza prova che sia semanticamente un puntatore valido.
- Processi remoti, core dump, altri sistemi/architetture e più thread sono rifiutati. Le versioni oltre la matrice collaudata non sono certificate.
- Sono dati istantanei: differenze fra snapshot non identificano l'istruzione che ha scritto, né dimostrano vulnerabilità/sfruttabilità. L'hash identifica i byte del binario, non autentica il produttore del dossier.

## Convalida ripetibile

```sh
python3 -m unittest discover -s tests -p test_debug_core.py -v
python3 scripts/validate-debug-linux.py work/r3-debug-NUOVO
```

Il secondo comando richiede Linux x86-64 e una cartella nuova. Compila il C nostro sia con simboli sia in copia `strip --strip-all`, registra i simboli dell'originale solo per predisporre breakpoint numerici nella copia senza simboli, ed esegue GDB `-nx`. Conserva comandi, codice di uscita GDB, log, snapshot, mappe grezze, hash del codice e strumenti. Il controllo usa `info registers`, `x/8i`, `x/8gx`, `x/64bx`, `info breakpoints`, mappe `/proc` e `info proc mappings` come riferimenti; i risultati non derivano soltanto dal JSON del modulo.

Controlli: due arresti, stesso run e snapshot distinti, byte e catena cambiati dopo continue; breakpoint attivo/disabilitato/pending; ricerca completa, limite risultati e confine PROT_NONE; ciclo, null, profondità e indirizzo illeggibile; limiti/input errati rifiutati; nessuna modifica dei registri o avanzamento target prodotto dai comandi. Un RSP reso intenzionalmente invalido dal test deve produrre stack indisponibile, poi il test ripristina il registro. Stato senza processo e dopo uscita rifiutati.

Esiti reali sotto; la ripetizione indipendente è conservata in `work/r3-debug-independent-001`, con gli stessi tre casi e 117 + 117 asserzioni.

## Fonti API consultate

- [GDB Frames in Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Frames-In-Python.html): frame più recente e lettura registri.
- [GDB Architectures in Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Architectures-In-Python.html): disassemblato a partire da un indirizzo, conteggio limitato.
- [GDB Inferiors in Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Inferiors-In-Python.html): processo selezionato, connessione e lettura memoria.

Le API sono verificate sull'effettivo GDB del laboratorio; consultazione online il 13 novembre 2026.

## Esito dell'implementatore

`work/r3-debug-002/validation.json`: **PASS**, due sessioni reali con 117 asserzioni ciascuna (simboli e copia senza simboli), più sessione senza inferior rifiutata con codice GDB 1 atteso. Non sono 235 programmi differenti: sono controlli di sezioni e casi negativi dentro tre sessioni. Quattro test offline del core superati; una mutazione intenzionale della terminazione dei puntatori è rilevata (`work/review-r3-debug-mutation/result.txt`).

Il tentativo `work/r3-debug-001` è conservato: la sessione con simboli era passata, ma la copia senza simboli aveva perso il permesso eseguibile nel programma di prova. Corretto il copia-file del validatore, poi ripetuto tutto in una cartella nuova. Nessun fallimento escluso è contato come convalida. Ripetizione indipendente e revisione integrata sono registrate separatamente dal coordinatore.

# R3c — vista strutturale heap

Aggiornamento R6: il profilo è esteso al build Kali glibc 2.43-4; differenze, ritorni e matrice in [R6.md](R6.md). Le prove 2.36 descritte sotto restano storiche.

Implementazione: `src/ressembly_heap_view.py`, `src/ressembly/heap_view_gdb.py`, nucleo indipendente `src/ressembly/heap_view.py`. Nessuna dipendenza da GEF, Pwndbg o Daybreak.

## Perimetro

Vista in sola lettura di un processo locale Linux x86-64 fermo, con un solo thread, glibc 2.36 e simboli di debug corrispondenti. Mostra header di un chunk indicato mediante **indirizzo utente** numerico; indirizzo, top, memoria di sistema e mutex di `main_arena`; dieci fastbin, 127 bin ordinari (unsorted/small/large) e 64 liste tcache del thread. Percorre catene forward limitate, decodifica safe-linking per fastbin e tcache e distingue conteggio dichiarato dai nodi letti. La terminazione indica null/sentinella, limite, ciclo, puntatore non allineato o memoria non leggibile.

La versione proviene dal simbolo `__libc_version` della libc effettivamente caricata. Tipi e simboli devono appartenere alla stessa libc, verificata nelle mappe locali; hash della libc e versione GDB sono inclusi nell'output. Gli offset derivano dai tipi di debug: in assenza di questi, o con layout/versione diversi, il comando rifiuta la vista. Non cerca offset alternativi. Target remoti e core dump sono esclusi esplicitamente. La presenza di più arene è rifiutata.

Matrice collaudata: Debian 12, kernel 6.1.0-54-cloud-amd64, glibc 2.36 Debian, GDB 13.1, Python GDB 3.11, QEMU TCG x86-64 sul Mac ARM64. Altre build con lo stesso numero di versione non sono automaticamente certificate.

## Uso ripetibile

Nel laboratorio Linux, dalla cartella del progetto:

```sh
gcc -g3 -O0 -fno-omit-frame-pointer -Wall -Wextra -Werror examples/heap_view_lab.c -o /tmp/ressembly-heap-view-lab
gdb -nx /tmp/ressembly-heap-view-lab
```

In GDB:

```text
source src/ressembly_heap_view.py
break heap_view_checkpoint
run
rs-heap-view
rs-heap-view arena 4
rs-heap-view arena 4 --json
p/x small_addresses[0]
```

Usare l'indirizzo restituito nell'ultimo comando come argomento numerico di `rs-heap-view chunk 0x...`. Le espressioni GDB non sono valutate dal comando: ciò evita chiamate involontarie al programma. Ogni `continue` raggiunge il checkpoint successivo: allocazioni iniziali, liberazione dei nove blocchi piccoli, liberazione del blocco grande, allocazione che ordina i bin. Tra esecuzioni confrontare ruolo e ordine dei nodi, non indirizzi assoluti.

Il comando scrive nel terminale; `--json` produce `ressembly.heap-structure.v1`. Non installa breakpoint, non modifica registri/memoria e non riprende il processo. Creare un nuovo `HeapView()` Python per ogni arresto: le istanze non sono un archivio persistente.

## Verifica

```sh
python3 -m unittest discover -s tests -p test_heap_view.py -v
python3 scripts/validate-heap-view-linux.py work/r3-heap-NEW
```

Il verificatore richiede una directory nuova e Linux x86-64; conserva sorgenti/hash, compilazione, comandi GDB, log grezzi, codici di uscita e JSON. Le 13 sessioni includono: percorso normale con campi GDB e byte dell'header come confronto; tre catene alterate deliberatamente in processi didattici separati; versione non supportata; simboli mancanti; nessun processo; limiti fuori intervallo; indirizzo non valido/non leggibile; espressione rifiutata; vista senza cambiamenti di PC, stack pointer, arena e breakpoint.

Nel percorso normale i controlli sono esterni al parser: `malloc(32)` produce chunk di 48 byte; sette blocchi liberati entrano in tcache in ordine LIFO e due in fastbin; il blocco da 0x500 entra nel bin unsorted e poi in un largebin. I puntatori attesi sono salvati dal C **prima** di `free`. Letture dei byte e campi `main_arena`/`tcache` tramite GDB sono registrate accanto alla vista Ressembly. La prova di rifiuto della versione altera il simbolo nel processo didattico fermo: non è una prova su una seconda distribuzione o libc.

Dossier autore: `work/r3-heap-002`, 13/13 sessioni superate sul codice con controllo esplicito della connessione locale; `work/r3-heap-001` conserva la prima esecuzione. I 4 test offline del nucleo sono superati. Il revisore indipendente ha ripetuto 13/13 sessioni in `work/r3-heap-independent-001`; prove supplementari e rapporto integrato conservano separatamente i risultati. Ogni nuova revisione richiede un nuovo dossier con gli hash finali.

## Limiti delle conclusioni

Una vista strutturale non è una cronologia. I flag nell'header non dimostrano che il chunk corrente sia allocato: `PREV_INUSE` descrive il chunk precedente. Un indirizzo arbitrario può somigliare a un header: il comando non autentica l'appartenenza a un'allocazione. `size_plausible` controlla soltanto dimensione/allineamento.

I bin sono percorsi mediante il collegamento forward; backward e `fd_nextsize`/`bk_nextsize` non sono verificati. Un ciclo o un conteggio discordante è una proprietà della lettura, non una diagnosi di corruzione sfruttabile. Una cattura dentro l'allocator può essere transitoria: fermarsi nel chiamante dopo il ritorno delle operazioni per interpretazioni stabili. Limite: 1–256 nodi **per lista**, massimo 201 liste; non è una scansione dell'intero heap o ricostruzione di tutte le allocazioni. Per mmap-chunk è disponibile soltanto l'interpretazione del singolo header indicato, non l'enumerazione dei blocchi mmap.

## Fonti primarie

- [glibc 2.36, malloc.c](https://github.com/bminor/glibc/blob/glibc-2.36/malloc/malloc.c): strutture e convenzioni di bin, header, tcache e safe-linking; consultato il 13 novembre 2026.
- [GDB, Types in Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Types-In-Python.html): appartenenza dei tipi all'objfile, campi, offset e array.
- [GDB, Inferiors in Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Inferiors-In-Python.html): connessione, thread e letture della memoria; API provate nel GDB 13.1 del laboratorio.

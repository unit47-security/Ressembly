# R5 — cronologia allocator estesa, profilo opt-in

Aggiornamento R6: il profilo è esteso al build Kali glibc 2.43-4; differenze, ritorni e matrice in [R6.md](R6.md). Le prove 2.36 descritte sotto restano storiche.

Questo modulo preserva la cronologia R2 e i suoi comandi. Si carica con
`source /percorso/Ressembly/src/ressembly_history.py` in GDB `-nx` e usa
`rshist-start FILE [EVENT_LIMIT]`, `rshist-continue`, `rshist-watch OBJECT_ID OFFSET WIDTH`,
`rshist-show`, `rshist-save`, `rshist-stop`. Una cattura per sessione; le catture v1/v2
sono mutuamente esclusive anche dopo la chiusura. Lo schema è
`ressembly.object-history.v2`, con `metadata.target_sha256` e UUID della cattura.

## Perimetro

Linux x86-64, GDB locale, processo avviato e singolo thread, glibc 2.36. Il profilo
usa gli ingressi esatti `__libc_malloc/free/calloc/realloc` e i ritorni osservati.
Gli ingressi vengono disabilitati durante ogni transazione: le chiamate interne
come realloc→malloc/free non vengono contate due volte. **Le chiamate annidate o
rientranti durante una transazione non sono coperte**, comprese eventuali chiamate
allocator da un signal handler. Il modulo non pretende tutte le operazioni allocator.

La base usa il motore già verificato per controllo del run, persistenza e ripresa;
il nuovo modello gestisce transazioni realloc e finestre distinte. Il cambiamento
R2 è limitato al rifiuto dell'avvio dopo una cattura v2, per evitare collector
contemporanei. Gli eventi precedenti non sono convertiti o riscritti.

## Semantica delle operazioni

- calloc conserva count, element_size, prodotto matematico e overflow size_t;
  l'eventuale azzeramento non diventa una sequenza di scritture osservate.
- realloc(NULL,n) produce una nuova allocazione al ritorno osservato, senza contare
  la chiamata malloc interna. Un oggetto di dimensione richiesta zero non offre una
  regione sorvegliabile.
- realloc nonzero fallita conserva identità e dimensione del vecchio oggetto.
- realloc riuscita chiude la vecchia identità e ne crea una nuova, anche allo stesso
  indirizzo, con relazione predecessore/successore. È una convenzione conservativa
  della cronologia, non l'affermazione che l'allocator abbia liberato fisicamente
  e riallocato la stessa memoria.
- realloc(nonnull,0) segue la policy glibc dichiarata: liberazione e risultato NULL.
  Non è una regola portabile di tutti gli allocator.
- Un ritorno mancante o un budget esaurito durante la transazione lascia lo stato
  `unknown_after_incomplete_realloc`; nessuna riuscita o free viene inventata.

## Regioni e riferimenti al codice

Fino a quattro regioni selezionate, di 1/2/4/8 byte naturalmente allineati, entro
la dimensione richiesta. Le sovrapposizioni sono rifiutate. Ogni finestra ha ID,
baseline, richiesta, attivazione, eventi e fine propri. Costruire un watchpoint non
prova l'inserimento hardware: si attiva la copertura soltanto dopo una ripresa
riuscita. Risorse esterne possono impedire l'inserimento; il fallback software è
rifiutato. Scritture dello stesso valore possono essere assenti.

Le finestre dell'oggetto terminano all'ingresso di free/realloc, prima delle
operazioni interne allocator. Anche se realloc fallisce occorre riselezionare
esplicitamente la regione: nessuna continuità di osservazione viene presunta.
Le finestre su altri oggetti rimangono separate.

Ogni evento osservato conserva il PC e, quando risolvibili, funzione, sorgente e
mappatura del modulo. `file_offset` è calcolato dal file offset della mappatura più
l'offset interno: **non è un RVA dal load base**. Per mappe senza file rimane ignoto.
Il caller all'ingresso è un return site, non l'istruzione call. Per i watchpoint il
PC è quello di arresto dopo l'istruzione; lo scrittore non viene attribuito.
Nessun segnale implica automaticamente vulnerabilità o sfruttabilità.

## Riproduzione e convalida

```sh
python3 -m unittest discover -s tests -p test_history_v2.py -v
python3 scripts/validate-history-v2-linux.py work/r5-history-NEW
```

Il C è nostro e non emette marker allocator. Le prove registrano argomenti e stati
con GDB, casi calloc/NULL/zero/fallimento/in-place/move, quattro regioni su due
oggetti, risorse hardware, fallback, memoria illeggibile, segnale, budget, ritorno
perso e conflitto tra collector. Un percorso separato GDB senza Ressembly verifica
byte zero, realloc in-place, spostamento e conservazione dopo fallimento.

Convalida Debian: 14 casi superati in `work/r5-history-003` e 14 nel replay
indipendente `work/r5-history-independent-001`, entrambi con hash dei sorgenti.
Cinque test del modello offline superati; mutazione della policy realloc zero
intercettata. La suite integrata carica anche i comandi rshist; due ordini di
caricamento e il ricaricamento sono verificati nel dossier
`work/r5-independent-regression-001`.
Il laboratorio Debian x86-64 emulato non attesta altre versioni glibc, Kali corrente,
prestazioni native, attach, fork, multithread o allocator diversi.

## Fonti primarie consultate

- [glibc 2.36 malloc.c](https://raw.githubusercontent.com/bminor/glibc/glibc-2.36/malloc/malloc.c), policy zero e percorsi interni realloc.
- [GNU realloc](https://sourceware.org/glibc/manual/latest/html_node/Changing-Block-Size.html), fallimento e conservazione del vecchio blocco.
- [GNU calloc](https://sourceware.org/glibc/manual/latest/html_node/Allocating-Cleared-Space.html), significato dell'azzeramento.
- [GDB watchpoint](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Watchpoints.html), risorse e inserimento alla ripresa.
- [GDB FinishBreakpoint](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Finish-Breakpoints-in-Python.html), ritorni e out-of-scope.

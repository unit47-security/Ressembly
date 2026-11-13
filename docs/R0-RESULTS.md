# R0 — risultati del confronto tecnico

13 novembre 2026. Esperimenti realmente eseguiti su programmi nostri nella VM Linux x86-64 emulata localmente con QEMU TCG sul Mac ARM64. **Non sono misure bare-metal, benchmark di ergonomia umana o prova di superiorità di Ressembly.** Il corpus è descritto in [R0-LABS.md](R0-LABS.md).

## Ambiente e identificazione

- Debian 12, kernel `6.1.0-54-cloud-amd64`, glibc 2.36.
- Runtime comune alle 30 sessioni selezionate: `GNU gdb (GDB) 18.1`, incluso nel pacchetto portable Pwndbg ufficiale `2026.10.28`; Python del runtime 3.13.11. Il pacchetto fornisce il runtime, mentre il loader Pwndbg sotto usa il checkout fissato.
- Pacchetto portable SHA-256: `17049a23ba8cbcf4780c4bc9b4aeb519f2801ceabe7304b55d3d622acca03b8c` (registrato nel provisioning del laboratorio).
- GEF: `809864d00442f9993298e33fd9cd282d687d2f45`; Pwndbg: `9760ac8f1346d142857cffc933995cd6fca34dff`.
- Source hash, binari, compilatore, GDB, libc host, loader hash, HEAD verificato e comandi esatti sono nei manifest di ogni profilo. I checkout erano puliti al lancio. Sono comparatori del laboratorio in `work/`, non dipendenze del prodotto.

## Evidenze conservate

Directory sotto `work/validation/r0/`:

| Profilo selezionato | Sessioni |
|---|---:|
| `r0-gdb-manual-002` | 6 |
| `r0-gef-manual-002` | 6 |
| `r0-pwndbg-manual-003` | 6 |
| `r0-gef-helper-002` | 6 |
| `r0-pwndbg-helper-003` | 6 |

Tutte le 30 sessioni selezionate hanno osservato exit 0 dell'inferior, checkpoint attesi e assenza dei segnali di setup-error controllati dal runner. `summary.json` conserva la matrice; `scripts/r0/verify-results.py` ha prodotto `consistent_30_raw_sessions`. Un controllo negativo su copia temporanea con conteggio trigger alterato è stato rifiutato (`negative-control.txt`). Questo verifica coerenza dei file, non autenticità indipendente della loro origine: l'esecuzione è attestata dai comandi realmente eseguiti nella sessione di lavoro e dai log.

## Ripetizione indipendente

Un agente separato ha eseguito altre 30 sessioni nei medesimi cinque profili, in nuove directory `work/validation/r0-independent/`. Runner, verificatore e sorgente C host/guest corrispondono agli hash conservati. I verificatori nel guest e sull'host hanno entrambi restituito `consistent_30_raw_sessions`; checkpoint, campioni e trigger riproducono la prima matrice. Le due serie costituiscono 60 sessioni valide, senza trasformare il test in uno studio di prestazioni o ergonomia umana.

## Confronto manuale comune

Stesso perimetro di watchpoint per tutti e tre gli strumenti; campioni e backtrace conservati prima e dopo. Le tre colonne indicano il numero di trigger osservati nella regione e finestra di vita selezionata, **non il numero di vulnerabilità**.

| Caso | GDB | GEF | Pwndbg | Osservazione verificata |
|---|---:|---:|---:|---|
| buffer good | 0 | 0 | 0 | Scritti otto byte logici, sentinel all'offset 8 invariato |
| buffer bad | 1 | 1 | 1 | Scritti dodici byte dello storage C da sedici; sentinel logico cambia |
| pointer good | 0 | 0 | 0 | Slot mantiene il puntatore alla prima funzione innocua |
| pointer bad | 1 | 1 | 1 | Slot sostituito con puntatore alla seconda funzione innocua |
| heap read good | 1 | 1 | 1 | Lettura osservata mentre l'allocazione è viva |
| heap read bad | 1 | 1 | 1 | Lettura osservata dopo il checkpoint di liberazione |

Per heap good/bad il trigger è identico: è la sequenza di vita a distinguerli. Non classificare good come UAF. La variante buffer è una violazione del limite logico dentro un array valido C, non una scrittura fuori dall'oggetto C: non si attribuisce a un heap helper l'obbligo di rilevarla. I campioni A16 → B8/A8 o B12/A4 e la modifica/non modifica dello slot sono verificati dal controllo della matrice. Il valore letto dopo free non è assunto né validato come risultato deterministico.

## Helper propri dei concorrenti

GEF `heap-analysis-helper` e Pwndbg `track-heap enable` sono stati eseguiti in profili separati, senza aggiungere i watchpoint manuali. Entrambi hanno prodotto log di allocazione/liberazione nei casi heap. Nessuno dei due ha fermato il solo accesso di lettura dopo free del corpus: in tutte le sessioni helper l'inferior ha raggiunto exit0 e i checkpoint attesi. Il codice fissato usa watchpoint di cambiamento di valore. Inoltre GEF sorveglia l’espressione `*addr` (regione iniziale di tipo int), mentre il campione legge all’offset +16: il test GEF non separa quindi mancata copertura spaziale e semantica di sola lettura. Pwndbg costruisce invece un’espressione array sul chunk. Il risultato riguarda questo accesso e questi profili, non dimostra la causa esclusiva di ogni eventuale evento mancante né osservazione di tutte le letture. Non viene dichiarato un bug dei concorrenti né una nuova tecnica di Ressembly.

Il controllo sul riuso degli indirizzi e le generazioni non è parte di questo corpus R0 e deve restare un gate specifico R2. Nessuna sessione R0 dimostra copertura di tutte le operazioni allocator o delle scritture intermedie.

## Tempi e passaggi registrati

La tabella seguente descrive la prima matrice: un'esecuzione per combinazione, in emulazione e con altre attività del laboratorio potenzialmente concorrenti. Il replay indipendente è conservato separatamente. Valori solo descrittivi del batch completo (startup/loader/debugger/target), non confronti di overhead del solo tracker.

| Profilo | Mediana batch secondi | Intervallo secondi | Righe comandi non vuote per caso |
|---|---:|---:|---:|
| GDB manual | 1.294 | 1.266–1.409 | 40 o 43 |
| GEF manual | 2.747 | 2.692–2.795 | 42 o 45 |
| Pwndbg manual | 9.062 | 8.313–9.516 | 43 o 46 |
| GEF helper | 3.125 | 2.748–4.112 | 33 |
| Pwndbg helper | 9.767 | 9.005–11.866 | 34 |

Le righe comprendono definizioni e comando di salvataggio; non equivalgono ad azioni manuali o tempo di un analista. Le ripetizioni per studiare variabilità/ordine e un confronto umano restano da fare prima di affermare vantaggi prestazionali o d'uso.

## Pilot esclusi e correzioni del percorso

I dossier `*-001` sono pilot: GEF falliva il caricamento per quoting del comando `source`; il primo GDB manual lasciava il watchpoint oltre il checkpoint finale, osservando anche il riuso successivo dello stack. Questi risultati non sono stati cancellati né usati per classificare il corpus.

I profili Pwndbg `*-002` raggiungevano exit0 ma riportavano `DEADLOCK DETECTED` e `SystemExit` con il flusso GDB `commands`/`continue`: classificati `setup-error`, esclusi. Le sessioni 003 usano il workaround indicato da Pwndbg (`disabled-deadlock` più resume tramite Python), senza quelle eccezioni. La configurazione differente è nei log/script. Le warning libthread_db presenti in alcune sessioni GDB/GEF del runtime portable riguardano questo laboratorio single-thread; nessuna compatibilità multi-thread è inferita.

## Decisione e limite di convalida

Il confronto tecnico mostra che i flussi esistenti osservano già i cambiamenti selezionati. Il problema concreto su cui valutare R2 è **conservare e rendere verificabile la relazione tra eventi allocator, generazioni d'allocazione e osservazioni di una regione**, evitando di interpretare un semplice trigger come verdetto. È una direzione di fattibilità; utilità aggiuntiva, originalità e superiorità rimangono ipotesi non dimostrate. Se la revisione R2 non mostra utilità concreta, rivederne priorità o forma senza ampliare per inerzia.

R0 dispone ora di una matrice tecnica ripetibile nel perimetro dichiarato. Non sono convalidati un beneficio umano, il comportamento su hardware nativo, Kali o altri allocator/versioni, né un detector generale di vulnerabilità.

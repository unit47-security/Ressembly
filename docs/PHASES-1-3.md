# Ressembly — chiusura fino a R3 inclusa

13 novembre 2026. Copia di lavoro: `/Users/user/Documents/ChatGPT/Ressembly`.

**R0, R1, R2 e tutti i moduli R3a–R3e sono implementati e convalidati nel perimetro del laboratorio dichiarato.** R4 (pacchetto alfa locale) non è incluso. La precedente dichiarazione “fasi 1–3” corrispondeva erroneamente a R1/R0/R2: lasciava fuori R3. Questo rapporto la sostituisce senza alterare o cancellare i risultati precedenti.

## Risultati verificati

| Modulo | Consegna effettiva | Prove finali |
|---|---|---|
| R0 | Confronto pratico GDB/GEF/Pwndbg su tre laboratori e controlli | 30 sessioni selezionate + 30 indipendenti, già conservate |
| R1a/R1b | Collector marker, JSON/terminale, errori, interruzioni e separazione dei run | 16 + 16 prove precedenti; altre 16 di regressione dopo R3 |
| R2a/R2b | malloc/free selettivi senza marker allocator, generazioni, regione hardware | 22 + 22 prove precedenti, oracolo separato e tre smoke di ampiezza; altre 22 di regressione dopo R3 |
| R3a/R3b | Assembly, breakpoint, registri, stack, mappe, dump, ricerca, catene | Tre sessioni GDB + tre indipendenti; 117 asserzioni sul target con simboli e 117 sullo stripped per esecuzione, più rifiuto senza target |
| R3c | Vista strutturale chunk/main_arena/fastbin/bin/tcache | 13 sessioni + 13 indipendenti; quattro prove Linux supplementari |
| R3d | Pattern, offset e proprietà ELF | 44 controlli + 44 indipendenti; 18 prove indipendenti supplementari |
| R3e | Input, snapshot, note, confronti, export e riapertura | 14 controlli + 14 indipendenti sul codice finale; riapertura da secondo revisore in processo separato, 10 controlli |
| Integrazione R2/R3 | Loader unico, collector e viste contemporanei, dossier integrato | Due sessioni × 20 controlli GDB + due sessioni indipendenti × 20; in ciascuna ulteriori controlli di uscita, generazioni, free ed export; conflitto con marker storico rifiutato |

Non sommare asserzioni, test unitari e sessioni come se fossero programmi o utilizzatori distinti. La riapertura da secondo revisore è stata eseguita da un agente separato; non è uno studio di usabilità su persone, previsto eventualmente per R4.

**Test locali finali: 67 Python e 14 JavaScript, tutti superati.** Le prove offline non sostituiscono GDB/Linux. Mutazioni intenzionali in copie separate hanno dimostrato che i test rilevano errori nelle generazioni, terminazione di catene, classificazione PIE e coerenza delle build. Non è un mutation score completo. La prova di 1000 mutazioni ELF è un controllo limitato del parser, non fuzzing esaustivo.

## Ambiente e confini

- Host Mac ARM64, QEMU 11.1.3 full-system TCG estratto localmente.
- Guest Debian 12 x86-64, kernel 6.1.0-54-cloud-amd64, glibc 2.36, GCC 12.2.0, binutils 2.40.
- R1/R2/R3: GDB 13.1, Python GDB 3.11.2. R0 usa il runtime comune GDB 18.1/Python 3.13.11 e revisioni dei comparatori fissate nei dossier.
- Un processo e un thread; vista heap iniziale per una sola arena, glibc 2.36 e simboli di debug corrispondenti.

È Linux/GDB reale dentro un guest emulato x86-64. **Non certifica Kali, hardware nativo, prestazioni fisiche, multi-thread o altri allocator/debugger.** Nessuna superiorità o innovazione dimostrata rispetto ai concorrenti. GEF/Pwndbg restano comparatori, non dipendenze.

Il prototipo HTML resta offline con dati sintetici. Il codice GDB/Python è distinto dal prototipo. Sono implementati i moduli iniziali previsti fino a R3, non una suite matura equivalente in ampiezza a GEF/Pwndbg né una release installabile già distribuita.

## Interpretazione corretta delle evidenze

L'allocator segnala allocazione/free; solo la regione hardware selezionata produce cambiamenti di valore osservati. Le scritture dello stesso valore possono non apparire. La copertura finisce prima della free e non si trasferisce automaticamente al riuso: il nuovo oggetto ha una nuova generazione. Un PC dopo l'istruzione non è automaticamente l'indirizzo dell'istruzione responsabile.

La vista heap è strutturale e istantanea: `PREV_INUSE` descrive il chunk precedente, non lo stato di vita del corrente. Le catene forward hanno limiti; link backward e nextsize non sono verificati. Memoria, ricerca e puntatori hanno budget espliciti e segnalano dati mancanti.

Le protezioni ELF sono proprietà statiche dichiarate; un simbolo canary non prova copertura di tutte le funzioni. Nessun singolo segnale produce un verdetto di vulnerabilità o sfruttabilità.

Gli esperimenti si riaprono come dossier, non ripristinano un processo. Input registrati non sono automaticamente input consumati. Build incompatibili e identità interne contraddittorie sono rifiutate. L'ID di processo e l'UUID di cattura hanno domini diversi: confronto `same_run: null` quando non sono direttamente comparabili. Hash e coerenza JSON non autenticano l'origine del dato.

## Difetti trovati e corretti

I collaudi precedenti hanno corretto quoting di `source`, fusione dei run, exit code dei validatori, registri unsigned, ritorni mancanti, calloc/realloc non supportate e budget dei watchpoint. R3 ha corretto il programma di prova che perdeva i permessi della copia stripped; l'import dei dossier che accettava contraddizioni fra metadati interni ed esterni (contesto e cronologie R1/R2); l'etichetta di confronto fra domini di identità diversi. Ogni correzione ha una verifica successiva; tentativi intermedi e falliti sono conservati, non contati come chiusure finali.

## Dossier finali locali

| Gruppo | Autore | Indipendente |
|---|---|---|
| Debugger/memoria | `work/r3-debug-002` | `work/r3-debug-independent-001` |
| Heap strutturale | `work/r3-heap-002` | `work/r3-heap-independent-001` |
| Strumenti lab | `work/r3-labtools-001` | `work/r3-labtools-independent-001` |
| Esperimenti | `work/r3-experiments-004` | `work/r3-experiments-independent-003` |
| Suite integrata | `work/r3-suite-003` | `work/r3-suite-independent-002` |

Aggiuntivi: `work/r3-heap-review-probes-002`, `work/r3-labtools-review-probes-001`, `work/review-r3-experiments`, `work/r3-integration-review-002`. Regressioni: `work/r3-r1-regression-001`, `work/r3-r2-regression-001`. Riepilogo e hash: `work/r3-gates/`.

Dossier precedenti conservati: `work/validation/r1-validation-005`, `r1-independent-001`, `r0/`, `r0-independent/`, `r2-validation-003`, `r2-independent-001`, `r2-primitive-oracle-001`, `r2-widths/`. Il precedente `work/gates/acceptance.json` copriva R0/R1/R2, non R3.

Guida d'uso e riproduzione: [R3.md](R3.md). Procedure dettagliate: [R1](R1-VALIDATION.md), [R0](R0-RESULTS.md), [R2](R2.md), [debug/memoria](R3-DEBUG.md), [heap](R3-HEAP.md), [lab](R3-LABTOOLS.md), [esperimenti](R3-EXPERIMENTS.md).

## Conservazione e prossimo confine

Originale `/Users/user/Documents/Codex/Projects/Ressembly`, prototipo e file storici sono conservati. Nessuna dipendenza Daybreak, servizio a pagamento, IA obbligatoria, push, pubblicazione o configurazione globale del Mac. La VM e i dossier restano locali; la VM è stata spenta ordinatamente, con processo terminato e conferma nel registro seriale (`work/r3-gates/lab-final-state.json`). `work/` contiene anche credenziali esclusivamente del laboratorio e immagini: è esclusa dai file da distribuire.

**Prossimo traguardo separato: R4**, pacchetto alfa locale, installazione/disinstallazione pulita, matrice Kali da verificare, guida e scelta della licenza. Non è stato avviato automaticamente e non implica autorizzazione alla pubblicazione.

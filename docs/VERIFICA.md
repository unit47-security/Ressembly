# Ressembly — verifiche correnti e storiche

## Chiusura corrente fino a R3 inclusa — 13 novembre 2026

R3a–R3e completate e convalidate nel laboratorio Debian 12 x86-64/QEMU TCG sul Mac ARM64, GDB 13.1, glibc 2.36. R4 non avviata. La precedente etichetta informale “fasi 1–3” copriva solo R1/R0/R2: la chiusura corrente corregge il perimetro.

| Modulo | Prove finali e indipendenti |
|---|---|
| R3a/b | Tre sessioni + tre indipendenti; 117 + 117 asserzioni su target con/senza simboli per esecuzione |
| R3c | 13 + 13 sessioni; quattro prove supplementari |
| R3d | 44 + 44 controlli; altri 18 indipendenti |
| R3e | 14 + 14 controlli; riapertura da revisore separato |
| Integrazione | Due percorsi × 20 controlli GDB, ripetuti indipendentemente, più controlli di storia/export |
| Regressioni | R1 16/16 e R2 22/22 dopo l'integrazione |
| Test locali | 67 Python, 14 JavaScript; nessun fallimento |

Dossier finali e limiti in [PHASES-1-3.md](PHASES-1-3.md); fonte aggregata `work/r3-gates/acceptance.json`. Guide in [R3.md](R3.md). Corrette le contraddizioni build/run accettate nei dossier e il confronto fra domini di identità diversi; test di regressione e replay finali conservati. Non sono dedotte autenticità, sfruttabilità, prestazioni native o superiorità dai PASS.

Il registro seguente è storico: i suoi conteggi e limiti temporali non sostituiscono lo stato corrente.



## Registro precedente: convalida R0/R1/R2 — 13 novembre 2026

**Convalidate nel laboratorio Debian 12 x86-64 emulato con QEMU TCG sul Mac ARM64.** Non sono convalide su hardware nativo né certificazione Kali. [Rapporto integrato](PHASES-1-3.md).

| Gate | Esito realmente osservato | Evidenze locali |
|---|---|---|
| R1a/R1b | 16/16 prove reali, ripetute indipendentemente 16/16 | `work/validation/r1-validation-005`, `r1-independent-001` |
| R0 pratico | 30 sessioni selezionate, ripetute indipendentemente altre 30 | `work/validation/r0`, `r0-independent` |
| R2a/R2b | 22/22 prove reali, ripetute indipendentemente 22/22 | `work/validation/r2-validation-003`, `r2-independent-001` |
| Oracolo regione R2 | GDB senza Ressembly: due cambiamenti A/B, scrittura A ripetuta non osservata come cambiamento | `work/validation/r2-primitive-oracle-001` |
| Ampiezze ulteriori | 2/4/8 byte, offset 0/primo byte modificato; non esaustivo di ogni offset/byte | `work/validation/r2-widths` |
| Test offline finali | 39 Python e 14 JavaScript superati; sintassi Python/shell verificata | `work/gates/python-tests-final.txt`, `javascript-tests-final.txt` |

R1/R2: GDB 13.1, Python 3.11.2, glibc 2.36. R0: runtime comune GDB 18.1/Python 3.13.11, checkout fissati e target sullo stesso guest. Hash dei sorgenti convalidati corrispondono ai file attuali. Revisione separata: corretti gli exit code nel validatore, la guard per realloc e lo stato budget nel watch; nessun difetto bloccante residuo trovato nel perimetro dichiarato. Una mutazione in copia temporanea delle generazioni è rilevata dai test; codice di produzione non alterato dalla prova.

Tutti i tentativi falliti e pilot sono conservati, esclusi dagli esiti validi. I tempi sono totali di subprocess nel guest emulato, non overhead isolato né prestazioni fisiche. Non sono dimostrati novità, superiorità o sfruttabilità. Gli eventi allocator rimangono separati dai cambiamenti di valore della sola regione osservata; scritture dello stesso valore e dati fuori copertura restano ignoti.

Il resto di questo file conserva il registro delle verifiche **precedenti a questa chiusura**: i gate Linux indicati allora come mancanti sono superati solo nel perimetro esplicitato qui sopra. Al momento di questo registro R3 era ancora esclusa; è ora convalidata dal nuovo registro sopra. Hardware nativo, Kali, altri allocator e multi-thread rimangono esclusi.


Aggiornamento 13 novembre 2026; le verifiche del 24 ottobre restano sotto come registro storico.

## Incremento: verificatore del laboratorio

Cartella corrente: `/Users/user/Documents/ChatGPT/Ressembly`, copia della precedente `/Users/user/Documents/Codex/Projects/Ressembly` conservata intatta. `work/` storico escluso dalla copia. Il codice del collector, del nucleo, del C didattico e del prototipo non è stato modificato in questo incremento.

**Difetto riprodotto prima della correzione:** `python3 -O scripts/verify-marker-history.py` sulla versione precedente accettava un file contenente solo `{"events": []}` con exit 0 e un messaggio che dichiarava acquisizione reale. Senza `-O` lo stesso file falliva. La riproduzione riguarda un file offline, non GDB.

**Correzione implementata:** controlli espliciti indipendenti da `assert`, verifica dei sette marker del nostro laboratorio, sequenze/provenienza dichiarata, identità per generazione, byte/differenze/dimensioni dei campioni e tabella finale degli oggetti. JSON malformato, chiavi duplicate, numeri non finiti e file oltre 2 MiB sono rifiutati. Uso errato: exit 2; input invalido/non leggibile: exit 1. Successo significa coerenza con le aspettative, non autenticità o acquisizione reale. Non è un validatore generale del formato suite.

**Verifiche eseguite in questa sessione:**

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v`: 18 test superati (9 storici e 9 nuovi, con più casi per test). CLI normale e ottimizzata, fixture con e senza riuso indirizzi, stati parziali/errore, input mancanti, incoerenti e oltre budget.
- `node --test tests/core.test.cjs`: 14 test superati.
- C compilato con `cc -std=c11 -g3 -O0 -fno-omit-frame-pointer -Wall -Wextra -Werror` ed eseguito sul Mac ARM64: exit 0, non-glibc esplicito. Non certifica Linux.
- Sintassi Python controllata senza importare GDB; `sh -n scripts/run-marker-lab.sh` riuscito. Il runner sul Mac ritorna exit 2 previsto, senza produrre acquisizioni Linux.
- Verifica di efficacia dei test: invertito il controllo dello schema in una copia temporanea, i test falliscono; la copia temporanea è stata rimossa, il codice corrente non è stato alterato dalla prova.
- Revisione di un agente separato: nessun difetto bloccante trovato nel perimetro; 18 test Python rieseguiti con successo. È una revisione statica/offline, non un test GDB.
- Confronto hash: originale conservato, prototipo e test precedenti invariati.

Nessuna dipendenza Daybreak o altra dipendenza esterna introdotta. Nessun push, pubblicazione o modifica globale. L'autenticazione di build/run/libc dal file resta fuori dal verificatore; i relativi metadati non sono una prova indipendente. Sessione reale GDB/Linux x86-64, benchmark concorrenti, overhead, hook allocator e watchpoint restano **non eseguiti**.

## Registro del 24 ottobre 2026

## R1a — risultati realmente osservati

- 9 test Python offline superati: generazioni su riuso, allocazione fallita, free ignota/null, campioni limitati e immutabili, lettura fallita, allocazione duplicata, budget eventi, input invalidi, rendering di errore senza contesto.
- Rieseguiti i 14 test JavaScript storici: tutti superati. Sintassi app/demo JavaScript verificata.
- C didattico compilato con Apple clang 17, `-std=c11 -g3 -O0 -fno-omit-frame-pointer -Wall -Wextra -Werror`; esecuzione Mac ARM64 exit 0, output esplicitamente non-glibc. Non certifica glibc/Linux.
- Sintassi Python e shell verificata. Lo script live rifiuta il Mac con exit 2 previsto e non produce un'acquisizione.
- Hash del prototipo e del test storico confrontati prima/dopo: invariati.
- Revisione integrata ha corretto quoting del controllo Python GDB e rendering degli errori privi di indirizzo. Nessuna revisione sperimentale dell'adattatore GDB riuscita: GDB non disponibile.

**Non eseguito:** sessione GDB, confronto manuale dei byte, test di interruzione nel debugger, laboratorio Linux/Kali x86-64, benchmark concorrenti, overhead, watchpoint o allocator hook. Nessun JSON di test offline è presentato come raccolta reale. Nessuna versione GDB/glibc è dichiarata supportata in produzione.

Percorso e gate: [R1A.md](R1A.md). Audit e classificazione delle evidenze: [AUDIT-2026-10-24.md](AUDIT-2026-10-24.md). R0 documentale parziale; R1a implementata ma validazione operativa aperta; R1/R2 non completati.

## Registro storico del prototipo HTML

Le sezioni seguenti riguardano il prototipo Windows storico, non il backlog attuale Linux.


## Verificato

- `node --test tests/core.test.cjs`: 14 test superati, zero fallimenti e zero skip.
- Sintassi `prototype/core.js`, `prototype/app.js` e `prototype/demo-data.js` verificata con Node.
- I test coprono ASLR, collisioni di simboli, moduli distinti, build incompatibili, scope diversi, dati parziali, eventi persi, provenienza, riferimenti evento/thread, valori RVA invalidi, sequenze non ordinate e assenza di mutazioni del bundle.
- Nessuna dipendenza JavaScript esterna, servizio cloud o esecuzione dei dati importati.

## Da verificare nelle milestone successive

Collector Windows x64, sessioni reali x64dbg, acquisizione di registri/memoria, importazione automatica di tracce native, connessione a Ghidra, supporto per file grandi e misure di beneficio con utilizzatori. Nessuna di queste capacità è attestata da M0.

## QA interfaccia

Aperta l’anteprima nel browser locale: interfaccia leggibile; indicatori verificati (3 funzioni solo B, 2 condivise, 2/6 ingressi). Il filtro Solo B lascia esattamente tre righe. Il dettaglio iniziale riporta B / evento #3. Non è stato completato il controllo end-to-end degli altri comandi: importazione, esportazione e tutte le interazioni richiedono ulteriore QA. Nessuna build desktop Windows eseguita. Il server temporaneo di anteprima è stato arrestato; i file restano apribili localmente.

## Aggiornamento R4/R5 — 13 novembre 2026

La precedente chiusura fino a R3 resta storica. Codice aggiunto, evidenze Linux/Ghidra, matrice Kali per modulo, prova umana e limiti correnti sono nel [rapporto R4/R5](PHASES-4-5.md). Gli esiti dei piloti non sostituiscono il collaudo dell'archivio finale; i relativi hash e validation.json rimangono esterni al pacchetto. Cleanup delle VM autorizzato dopo i test, evidenze conservate sull'host.

## Aggiornamento R6 — 13 novembre 2026

Profilo glibc 2.43-4 su Kali: 24 gruppi reali, regressione target 2.36 in sysroot isolato: 16 gruppi, entrambi con R2 22 casi e R5 14 casi annidati. 97 test Python e 14 JavaScript. Oracolo GDB separato, mutazione intercettata, version probe e helper-stop verificati. [Rapporto R6](R6.md). Accettazione del pacchetto, replay indipendente e pulizia effettiva sono registrati in `work/r6-gates/acceptance.json`. Nessuna prestazione nativa attestata o pubblicazione eseguita.

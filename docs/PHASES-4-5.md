# R4 e R5 — rapporto locale e confini della convalida

13 novembre 2026. R4 consegna l'alfa locale installabile; R5 comprende la cronologia estesa concordata, Ghidra offline e plugin locali. Non è una pubblicazione né una suite completa per ogni piattaforma. La licenza scelta dall'utente è **GPL-3.0-or-later**, con testo in LICENSE e applicazione/esclusioni in NOTICE. Nessuna dipendenza da Daybreak, GEF, Pwndbg o IA obbligatoria.

## Evidenze osservate

| Area | Prove effettive e dossier conservati |
|---|---|
| Contratti offline | 93 test Python e 14 JavaScript, `work/r4-r5-gates/python.txt` e `javascript.txt` |
| Pacchetto pilota003 | 16 controlli Debian (`work/r4-package-debian-001`) e 16 Kali (`work/kali-lab/package-pilot003`), installazione senza checkout del prodotto |
| Moduli installati Kali pilota | 10 controlli `work/kali-lab/installed-pilot003`: contesto/memoria/plugin/dossier/statico; rifiuto dei profili glibc incompatibili |
| Cronologia R5 | 14 controlli reali in `work/r5-history-003`, altri 14 nel replay indipendente `work/r5-history-independent-001`; oracolo GDB separato, mutazione intercettata |
| Ghidra | 27 controlli `work/r5-ghidra-validation-002`, due ELF PIE/non-PIE e otto negativi diretti; diagnostiche specifiche verificate separatamente |
| Plugin | Nove test di contratto e 17 controlli/due sessioni GDB in `work/kali-lab/plugins-validation/002`; mutazione dell'hash fidato intercettata |
| Prova umana | Esito positivo riferito dall'utente, `work/r4-r5-gates/user-trial.json`; difficoltà iniziale di incollaggio risolta con un comando per riga |

Il pacchetto conclusivo si distingue dai piloti: due build byte-identiche e hash esterni in `work/r4-r5-final-build.json`; installazione finale Debian in `work/r4-package-debian-final`, Kali in `work/kali-lab/package-final` e matrice installata in `work/kali-lab/installed-final`. **L'esito conclusivo va letto nei relativi validation.json: questa tabella non attribuisce ai piloti la validazione di byte successivi.** I digest finali restano esterni al ZIP per evitare un riferimento circolare fra archivio e documento contenuto. Non includiamo dossier, VM o chiavi nel pacchetto.

## Matrice e limiti

Debian 12 x86-64, GDB 13.1/Python 3.11/glibc 2.36: moduli generali, heap e cronologia selettiva. Kali 2026.3 x86-64, GDB 17.2/Python 3.14.7/glibc 2.43: moduli generali; **heap e collector allocator R2/R5 non supportano glibc 2.43 e la rifiutano esplicitamente**. Kernel/processi Linux reali in QEMU TCG sul Mac ARM64; nessuna misura di prestazioni native. Ghidra 12.1.4 con JDK21 gira sul Mac usando ELF/riferimenti acquisiti in Linux, non dimostra debugging Linux sul Mac.

La cronologia R5 è opt-in, singolo processo/thread, fino a quattro regioni hardware selezionate. calloc e realloc sono operazioni allocator; non ricostruiscono tutte le scritture. Realloc riuscita crea una nuova identità anche allo stesso indirizzo; regioni sospese/terminate richiedono nuova selezione. Ritorni mancanti e budget esauriti producono stati incompleti espliciti. Chiamate rientranti/nidificate durante una transazione non sono coperte. [Semantica completa](R5-HISTORY.md).

I plugin generano annotazioni separate: processo separato **non significa sandbox**; codice fidato eseguito con i permessi dell'utente. Il bridge Ghidra verifica identità e coerenza, non autenticità. Nessun segnale isolato dimostra sfruttabilità.

## Confronto aggiornato: documentazione, non nuovo benchmark

Le fonti primarie consultate il 13 novembre confermano funzionalità già esistenti: [GEF context](https://hugsy.github.io/gef/commands/context/) presenta registri, codice, stack e contesto; [GEF heap-analysis-helper](https://hugsy.github.io/gef/commands/heap-analysis-helper/) documenta analisi di operazioni heap. [Pwndbg features](https://pwndbg.re/dev/features/) e [indice comandi stabile](https://pwndbg.re/stable/commands/) includono contesto, heap e `track-heap`. Queste capacità impediscono di presentare generici contesto o tracking allocator come invenzioni Ressembly. Il confronto sperimentale R0 conserva versioni fissate e problemi circoscritti nel [rapporto R0](R0-RESULTS.md); consultare documentazione corrente non equivale a rieseguire quei benchmark sulle ultime versioni.

Rimane un'ipotesi di prodotto, non una superiorità dimostrata, che identità di oggetto, copertura selettiva esplicita e dossier persistenti semplifichino alcuni laboratori. La prova umana positiva riguarda il percorso indicato, non produttività comparativa.

## Conservazione e seguito

L'utente ha autorizzato, dopo i collaudi finali, la rimozione di entrambe le VM, immagini/base download, runtime QEMU locale e chiavi dedicate. Log, manifest e dossier sull'host rimangono; il coordinatore registra l'effettiva rimozione e spazio recuperato in `work/cleanup-report.json`. I vecchi script SSH/avvio diventano riferimenti storici non utilizzabili senza ricostruire il laboratorio. La cartella originale del progetto rimane preservata.

Prossimo gate proposto: supporto allocator glibc 2.43 con corpus/oracoli dedicati, oppure prova su hardware x86-64 fisico. Attach/fork, multithread, altri allocator, GUI e backend alternativi restano non implementati. Nessun repository remoto, push, release o servizio a pagamento introdotto.

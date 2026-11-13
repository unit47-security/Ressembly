# Preparazione alla prima alfa GitHub

13 novembre 2026. Questa preparazione non pubblica né carica nulla. Destinazione desiderata dall'utente: GitHub. La decisione finale di creazione del repository, visibilità e caricamento rimane esplicita.

Il perimetro proponibile è **alfa sperimentale 0.6.0**, Linux x86-64/GDB/Python, GPL-3.0-or-later. Non presentare il progetto come suite universale completa, migliore di GEF/Pwndbg o capace di dedurre sfruttabilità automaticamente.

## Materiale preparato

- Sorgenti, programmi C nostri, test e validatori ripetibili.
- LICENSE completa e NOTICE per il codice originale; strumenti esterni non inclusi né rilicenziati.
- README, roadmap, installazione/disinstallazione locale e limiti per modulo.
- Pacchetto deterministico, manifest SHA-256 e verifiche di installazione; esito conclusivo in `work/r6-gates/acceptance.json`.
- `.gitignore` esclude `work/`, bytecode e metadati Finder. Immagini VM, chiavi, dossier e dipendenze scaricate non appartengono al materiale da caricare.
- Scansione limitata di pattern di chiavi/token sui file di testo: esito in `work/r6-gates/publication-pattern-scan.json`; non costituisce una prova esaustiva di assenza di segreti.

## Come presentarla

Dichiarare i build effettivamente provati, l'emulazione TCG sul Mac e la regressione 2.36 in ambiente misto. Versioni vicine come 2.43.1, hardware nativo, multithread, attach/fork, altri allocator e GUI non sono convalidati. Ghidra è un bridge offline; i plugin sono codice fidato con i permessi dell'utente, non una sandbox.

Non caricare l'intera cartella di lavoro senza una selezione. La prima pubblicazione dovrà selezionare sorgenti, esempi, test, integrazioni, guide e licenza; per una release allegare solo il pacchetto conclusivo e il relativo checksum. I checksum attestano coerenza, non autenticità del produttore.

Prima del caricamento verificare che l'acceptance finale sia PASS e scegliere con il proprietario account/organizzazione, nome repository e visibilità. Nessun repository remoto o workflow di pubblicazione è stato creato da R6. Nome e marchio non risultano verificati.

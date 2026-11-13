# R5 — collegamento offline a Ghidra

Il bridge correla un riferimento GDB con **lo stesso ELF** usando SHA-256, file offset, byte originali e indirizzo virtuale ELF. Non controlla una sessione Ghidra già aperta e non implica una sincronizzazione continua del debugger. Ghidra e JDK sono strumenti esterni scelti esplicitamente; non vengono scaricati o installati dal prodotto.

In GDB fermato sul programma proprio, dopo il caricamento della suite:

```gdb
rs-code-reference reference.json
```

Nel terminale, per un'installazione locale (sostituire i percorsi):

```sh
PREFIX/bin/ressembly ghidra validate reference.json /percorso/programma
PREFIX/bin/ressembly ghidra analyze reference.json /percorso/programma --ghidra-home /percorso/ghidra_12.1.4_PUBLIC --java-home /percorso/jdk-21 --workdir /percorso/analisi-nuova
```

Dal checkout si usa `python3 scripts/ressembly-ghidra.py` al posto di `PREFIX/bin/ressembly ghidra`. Racchiudere tra virgolette i percorsi con spazi. `validate` controlla coerenza del riferimento e del file senza Ghidra. `analyze` richiede una cartella nuova, importa una copia nel progetto locale e conserva comando, log e `ghidra-link.json`. Cache, impostazioni e file temporanei sono confinati nella cartella dell'analisi mediante argomenti JVM; non viene salvata una configurazione globale del launcher.

L'output identifica funzione e indirizzo risolti. Un file offset **non è un RVA dal load base**. Per PIE si mantiene la corrispondenza attraverso il segmento ELF e la mappatura Ghidra; i numeri degli indirizzi runtime e Ghidra possono differire. Un PC di watchpoint indica l'arresto dopo l'istruzione, non identifica automaticamente l'istruzione che ha scritto. Riferimenti anonimi o non risolvibili non diventano collegamenti inventati.

Sono rifiutati hash diverso, offset frazionario/fuori uint64, mappatura runtime contraddittoria, indirizzo ELF incoerente, chiavi JSON duplicate nello script e byte modificati nel programma importato. Un risultato esistente non viene sovrascritto. Il solo codice di uscita zero di Ghidra non basta: lo script può fallire lasciando l'applicazione con exit zero, perciò il risultato richiesto deve esistere e mantenere l'identità attesa. La coerenza di un JSON non ne dimostra autenticità.

Convalida effettiva: `work/r5-ghidra-validation-002/validation.json`, **27 controlli superati**, due importazioni complete PIE/non-PIE e otto importazioni negative dirette. ELF/riferimenti acquisiti realmente in Linux, confronto indipendente con GNU nm/readelf e byte; Ghidra 12.1.4/JDK 21 eseguiti sul Mac ARM64. I percorsi con spazi sono inclusi. Diagnostica negativa controllata separatamente in `negative-diagnostics-review.json`. Il tentativo 001 è escluso perché lo script Java cambiò durante il test, intercettato dal controllo hash finale.

Riproduzione sviluppatore: `scripts/validate-ghidra-local.py` richiede corpus Linux con riferimenti e oracoli nm/readelf, percorsi Ghidra/JDK espliciti e directory nuova. Non è incluso nel pacchetto utente. Non sono convalidati altri formati binari, architetture o versioni Ghidra; il bridge non dimostra vulnerabilità o sfruttabilità.

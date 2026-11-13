# R3e — esperimenti persistenti

Implementato e collaudato con snapshot reali GDB; risultati e ripetizioni indipendenti sono nel [rapporto finale](PHASES-1-3.md).

Il dossier `ressembly.experiment.v1` è un JSON autonomo: identità e SHA-256 del
binario, input binari in base64, snapshot selezionati, annotazioni riferite agli
snapshot e limiti espliciti. Si può riaprire senza GDB e senza il processo originale.
Non ripristina un processo, non riproduce automaticamente una sessione e non esegue
gli input o eventuali stringhe presenti nei dati.

## Percorso locale

```sh
python3 scripts/ressembly-experiment.py create work/experiment.json work/owned-binary "Esperimento nostro"
python3 scripts/ressembly-experiment.py input work/experiment.json work/input.bin "Input previsto"
python3 scripts/ressembly-experiment.py show work/experiment.json
python3 scripts/ressembly-experiment.py note work/experiment.json "Osservazione" --snapshot ID
python3 scripts/ressembly-experiment.py compare work/experiment.json ID1 work/experiment.json ID2
python3 scripts/ressembly-experiment.py export work/experiment.json work/export.json
```

Lo snapshot reale è acquisito dal comando GDB `rs-experiment-snapshot FILE LABEL [ADDRESS LENGTH]`,
dopo `source /percorso/Ressembly/src/ressembly_experiment.py`.
L'importazione offline usa `import-snapshot FILE SNAPSHOT_JSON BUILD_SHA256 RUN_ID LABEL`:
questa provenienza è `supplied_json`, non una prova di acquisizione tramite GDB.
Gli schemi noti debug-context, object-history R2 e marker-history R1 devono avere hash build e run interni coerenti con il record; il dossier rifiuta le contraddizioni senza modificarsi. Il file conserva questa distinzione. Anche `gdb_context` è una provenienza dichiarata,
non una firma crittografica: gli hash rilevano incoerenze, non attestano autenticità.

## Confronti e limiti

Build diverse sono rifiutate, anche per il confronto. Run dello stesso dominio diversi sono permessi ma
segnalati: i valori grezzi e gli indirizzi non costituiscono identità di oggetti.
Gli ID di processo (boot/PID/start) e gli UUID delle catture hanno domini diversi: il confronto li dichiara non confrontabili (`same_run: null`). La differenza fra due snapshot non ricostruisce le scritture intermedie. Ogni
sezione parziale resta tale; il dossier non trasforma dati mancanti in osservazioni.
Un input registrato non è automaticamente un input consumato dal programma.

Budget: binario di riferimento 256 MiB, dossier 8 MiB, singolo input 256 KiB, snapshot 1 MiB, fino a 128 record per
collezione, nota 16.384 caratteri. Nessun overwrite implicito in creazione/export.
Aggiornamenti scritti su un file temporaneo con fsync e sostituzione atomica;
un lock esclusivo evita scrittori simultanei che usano questo percorso. Dopo un
arresto forzato il lock può restare: verificare che non ci siano scrittori attivi
prima di rimuoverlo manualmente. Non è promesso recupero dopo ogni guasto di disco.
Il dossier è locale e può contenere input e memoria sensibili; l'export è una copia
integrale, senza invio a servizi esterni.

Fonti API GDB: [comandi Python](https://sourceware.org/gdb/current/onlinedocs/gdb.html/CLI-Commands-In-Python.html),
[inferior e lettura memoria](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Inferiors-In-Python.html).

# R1a — marker e campioni di un programma nostro

Aggiornamento 13 novembre 2026: percorso marker R1a e affidabilità R1b convalidati su Debian 12 x86-64 in emulazione QEMU TCG, con 16 prove reali e 16 ripetute da un agente separato. Vedi [convalida R1](R1-VALIDATION.md). Questo non certifica hardware nativo o Kali, né il tracker generale della suite.

## Perimetro

`examples/marker_lab.c` usa malloc/free reali, ma comunica solo operazioni selezionate tramite `rs_event(kind, ptr, size)`: 1 allocazione restituita, 2 dichiarazione dopo free completato, 3 richiesta di campione. Nessuna lettura di memoria liberata. Il riuso della seconda allocazione dipende dall'allocator: non è garantito. Il test offline forza il riuso per verificare identità distinte.

`src/ressembly/history.py` assegna una generazione per indirizzo. Una liberazione non marcata resta ignota. `src/ressembly_gdb.py` raccoglie marker con breakpoint Python e legge al massimo 64 byte per campione, con budget di 10000 eventi. Le differenze indicano offset cambiati nei byte confrontabili; `None` significa nessun campione precedente, non zero scritture. Lo stato resta a copertura parziale anche dopo uscita normale.

Non sono supportati target arbitrari, attach, multi-processo/thread, realloc, calloc, allocator alternativi, parsing heap o scritture puntuali. Il runner limita l'acquisizione a Linux x86-64 con glibc e Python GDB >=3.9; La convalida operativa riguarda GDB 13.1, Python 3.11.2 e glibc 2.36 del laboratorio Debian; altre combinazioni non sono certificate. Non dipende da GEF, Pwndbg, IA o servizi. La loro coesistenza non è testata: usare GDB `-nx`.

## Percorso Linux da eseguire

Dalla cartella del progetto, in un ambiente Linux x86-64 autorizzato con compilatore C, glibc, GDB con Python e Python 3:

```sh
sh scripts/run-marker-lab.sh work/linux-r1a-001
python3 scripts/show-marker-history.py work/linux-r1a-001/history.json
```

La directory deve essere nuova. La procedura compila con simboli e ottimizzazione disabilitata, avvia GDB senza configurazione personale, salva JSON/log e confronta gli eventi attesi. Successo atteso: sette marker, secondo campione diverso solo all'offset 4, due identità oggetto distinte, entrambi liberati, exit 0. Il successo dello script non dimostra un confronto con concorrenti o la completezza delle scritture.

Uso manuale dopo compilazione, dalla root del progetto:

```text
gdb -nx -q work/linux-r1a-001/marker_lab
source src/ressembly_gdb.py
rs-start work/manual-history.json
run
rs-show
rs-save
```

Una sola acquisizione per sessione GDB. `rs-save` conserva lo stato corrente; uscita del processo, signal stop e uscita normale di GDB hanno salvataggi dedicati. Arresto forzato/crash del debugger possono perdere dati successivi all'ultimo salvataggio. Dopo un'interruzione prima dell'uscita lo stato non deve essere presentato come sessione conclusa. Non eseguire un secondo `run` nella stessa acquisizione.

## Contratto e provenienza

Schema `ressembly.marker-history.v1`, indipendente dallo schema HTML storico. Metadati: UUID run, SHA-256 e percorso del binario, host/GDB/architettura, libc host (non prova della libc caricata), stato processo/acquisizione. Conservare anche l'output del target con versione glibc effettiva dichiarata e i file ambiente del runner. Ogni marker normale include sequenza, thread, PC, tipo, indirizzo, dimensione e identità quando risolta. Gli errori del collector possono avere contesto incompleto e restano errori, non eventi inferiti.

`explicit_target_marker` è una dichiarazione del target: non un hook indipendente dell'allocator. `bytes_hex` proviene da una lettura GDB al marker. Il PC del marker non identifica l'istruzione che ha modificato i byte. Nessuna normalizzazione modulo/offset o equivalenza fra puntatori di esecuzioni differenti è implementata. Le esportazioni contengono indirizzi e campioni: dati di laboratorio, da non confondere con tracce sintetiche o con un rapporto di vulnerabilità.

## Test offline e prossimo gate

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/core.test.cjs
```

I test Python sono dati costruiti offline, non acquisizioni reali. Il gate successivo è eseguire e controllare manualmente il percorso Linux: marker, `x/32bx` ai checkpoint, thread, indirizzi/generazioni, log e hash. Aggiungere poi casi di interruzione/errore e misurare overhead. Solo dopo scegliere hook allocator e regione watchpoint, con limiti espliciti e benchmark GEF/Pwndbg.


## Verificatore del laboratorio — aggiornamento 13 novembre 2026

Il verificatore è dedicato ai sette marker di `marker_lab.c`, non è un validatore generale della suite. I controlli devono restare attivi anche con `python3 -O`: nessuna accettazione dipende da `assert`. Il budget del file di input è 2 MiB; JSON malformato, chiavi duplicate e numeri non finiti sono rifiutati. Uso errato ritorna exit 2; file invalido o non leggibile exit 1. Il file deve essere coerente su sequenze, indirizzi, identità per generazione, campioni, oggetti finali e copertura dichiarata. Un risultato positivo attesta solo che il file rispetta le aspettative del laboratorio: non autentica la provenienza, non dimostra un'esecuzione reale e non misura la copertura delle scritture.

I dati costruiti dai test sono fixture sintetiche in memoria o in directory temporanee, con campi costruiti anche quando imitano quelli del collector; non diventano acquisizioni reali. Il visualizzatore rimane un lettore preliminare di file locali fidati, non un attestatore della loro autenticità.

La copia di lavoro corrente è `/Users/user/Documents/ChatGPT/Ressembly`; l'originale del 24 ottobre resta nella posizione precedente. Il successivo intervento del 13 novembre ha eseguito il gate Linux x86-64 e il confronto manuale in GDB nel laboratorio emulato, come documentato in R1-VALIDATION.md. Nessuna dipendenza Daybreak è introdotta.

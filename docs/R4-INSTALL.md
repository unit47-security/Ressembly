# R4 — pacchetto alfa locale

Il pacchetto contiene codice Ressembly, esempi nostri, guide, licenza e avvisi. Esclude `work/`, immagini VM, chiavi, acquisizioni, cache, comparatori GEF/Pwndbg e prototipo HTML. Nessuna pubblicazione o invio in rete. Licenza del codice del progetto: vedere `LICENSE` e `NOTICE`; i programmi esterni restano separati.

## Creazione e verifica

Dalla cartella sorgente, con Python 3.9 o successivo:

```sh
python3 scripts/build-local-package.py work/ressembly-0.5.0-local.zip
```

L'output deve essere nuovo. La costruzione usa una lista di directory, suffissi e CLI ammessi; non archivia l'intera cartella del progetto. Il manifest registra percorso, dimensione, modalità e SHA-256 di ogni file. Due costruzioni con identici file ammessi producono byte identici. Il checksum rileva incoerenze, **non autentica il produttore**. Le copie dei file storici conservate nel sorgente non sono una funzionalità operativa aggiuntiva.

Limiti dell'archivio: 32 MiB, fino a 512 file, singolo file 2 MiB, totale contenuti 24 MiB. Il formato locale ammette solo file regolari ZIP non compressi, percorsi relativi nel layout previsto, nessun link o entry duplicata. Non è un estrattore ZIP generico.

## Installazione in spazio utente

Su Linux x86-64, come utente ordinario, dalla cartella sorgente:

```sh
mkdir -p "$HOME/.local"
python3 scripts/install-local.py install work/ressembly-0.5.0-local.zip "$HOME/.local/ressembly-alpha"
"$HOME/.local/ressembly-alpha/bin/ressembly" verify
"$HOME/.local/ressembly-alpha/bin/ressembly" doctor
"$HOME/.local/ressembly-alpha/bin/ressembly" --help
```

La directory padre deve già esistere e appartenere all'utente. Il prefisso deve essere nuovo, senza symlink lungo il percorso. Per una nuova versione usare un altro prefisso; non è previsto un aggiornamento distruttivo in-place. Sono supportati spazi nei percorsi; citare gli argomenti come negli esempi. `root` è rifiutato. Nessuna scrittura in `.gdbinit`, profili shell, PATH globale o directory di sistema; nessuna installazione automatica delle dipendenze. Il pacchetto non richiede pip, servizi web o IA. Per eseguire gli esempi serve anche un compilatore C.

Il comando `doctor` scopre ambiente, Python, GDB/Python e libc del sistema. Distingue i prerequisiti generali dal profilo heap e segnala libc host non supportata; i moduli heap verificano nuovamente la **libc effettivamente caricata nel processo**. Una discovery riuscita non costituisce convalida operativa, né garantisce simboli glibc disponibili. La matrice effettivamente collaudata è registrata dal rapporto R4/R5.

Layout installato:

- `bin/ressembly`: launcher locale;
- `lib/ressembly/src`: moduli GDB/Python;
- `lib/ressembly/scripts`: CLI offline;
- `lib/ressembly/examples`, `integrations`, `docs`: esempi, bridge e guide;
- `.ressembly-manifest.json`: registro dei file installati.

Matrice aggiornata dei profili allocator: [R6.md](R6.md). La versione 0.6.0 aggiunge il build Kali glibc 2.43-4; le evidenze R4/R5 restano storiche.

## Primo avvio

Creare il binario e i risultati **fuori dal prefisso di installazione**:

```sh
mkdir work/alpha-demo-001
cc -g3 -O0 "$HOME/.local/ressembly-alpha/lib/ressembly/examples/heap_lab.c" -o work/alpha-demo-001/heap_lab
"$HOME/.local/ressembly-alpha/bin/ressembly" gdb work/alpha-demo-001/heap_lab
```

Dentro GDB, inserire **un comando alla volta** e premere Invio dopo ciascuno. `set pagination off` disattiva le pause di visualizzazione:

```gdb
rs-help
break lab_ready
run
rs-context
rs-maps
```

Il launcher usa GDB `-nx`, disabilita l'autocaricamento e carica la suite dal proprio prefisso mediante un bootstrap Python: nessuna concatenazione di comandi shell. Gli argomenti passati dopo `gdb` sono normali argomenti GDB. Per raccolta heap, simboli glibc e funzioni aggiuntive seguire le guide dei moduli e la matrice verificata.

CLI offline disponibili:

```sh
"$HOME/.local/ressembly-alpha/bin/ressembly" lab --help
"$HOME/.local/ressembly-alpha/bin/ressembly" experiment --help
"$HOME/.local/ressembly-alpha/bin/ressembly" plugins --help
"$HOME/.local/ressembly-alpha/bin/ressembly" ghidra --help
```

Gli ultimi due comandi hanno i rispettivi confini e procedure di fiducia descritti dalle guide dell'estensione. Il launcher non installa Ghidra né abilita automaticamente plugin.

## Disinstallazione e conservazione dei dati

```sh
"$HOME/.local/ressembly-alpha/bin/ressembly" uninstall
```

Prima della rimozione vengono controllati manifest, contenuto, modalità, percorsi e inventario completo. Se un file è cambiato, se compare un link, una cartella o un file non previsto, il comando si ferma **prima di rimuovere file**. Non elimina ricorsivamente contenuti sconosciuti. Esaminare e conservare manualmente ciò che è stato aggiunto/modificato, quindi riprovare; non esiste `--force`.

Non aggiungere note, plugin personali o dossier dentro il prefisso: mantenerli in cartelle di lavoro separate. L'installazione/disinstallazione presuppone che nessun altro processo modifichi contemporaneamente quel prefisso. Un'interruzione durante l'installazione può lasciare un prefisso incompleto; non viene automaticamente eliminato al tentativo successivo. Verificarlo prima di rimuoverlo manualmente. L'operazione non promette transazioni resistenti a ogni guasto di disco.

## Collaudo

Test offline del confezionamento: `python3 -m unittest discover -s tests -p test_packaging.py -v`.

La convalida Linux viene eseguita dal percorso `scripts/validate-package-linux.py` in directory nuova: due build riproducibili, installazione pulita in prefisso con spazi, verifica, avvio reale GDB su C nostro, CLI, rifiuto di pacchetto manomesso, conservazione di file aggiunti e disinstallazione. È possibile passare un archivio già costruito come secondo argomento (`NEW_DIRECTORY EXISTING_ZIP`): in questo caso il controllo dichiara esplicitamente che la riproducibilità della build non è verificata sul guest. Il risultato deve essere conservato separatamente per ogni distribuzione. I test offline sul Mac non attestano GDB/Linux o Kali.

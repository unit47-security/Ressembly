# Diagnostica di processi, allocator e selezioni Ghidra

Queste funzioni sono nella copia di lavoro. Gli archivi precedenti della 0.8.0 conservano il proprio contenuto.

## Processi e thread

```sh
python3 -B scripts/ressembly-diagnostics.py demo processes.json
python3 -B scripts/ressembly-diagnostics.py demo fork-processes.json --method fork
```

Il comando dimostrativo avvia due figli del supervisore. Ogni figlio registra due thread e una barriera fa sì che entrambe le sezioni siano aperte contemporaneamente. Il supervisore verifica l'uscita dei figli e salva il rapporto. Il metodo predefinito è `spawn`. `fork` è disponibile sui sistemi in cui Python lo supporta. Nel pacchetto locale il comando equivalente inizia con `ressembly diagnostics`.

Per applicazioni cooperanti, `ressembly.diagnostics.ProcessLog` si istanzia nel processo che emette il log. `with log.thread("etichetta")` racchiude la sezione da registrare. `log.close()` restituisce la scheda dopo la chiusura di tutte le sezioni. La relazione con il padre si dichiara con `ProcessLog("figlio", parent_id=parent_id)`. Un log ereditato da fork va sostituito con un nuovo log del figlio. `report` raccoglie le schede e `write_new` salva su un percorso nuovo su un filesystem con supporto agli hard link.

Gli identificativi del report distinguono le istanze anche quando PID e TID vengono riusati. Sequenza e tempo trascorso appartengono a ciascun processo. Gli eventi riportano sezioni dichiarate dall'applicazione. Ogni processo ha un limite di 128 eventi. Il supervisore del demo osserva i codici d'uscita. L'aggancio a processi arbitrari e la cronologia degli oggetti heap fra thread, arene e processi restano nella roadmap.

## Statistiche jemalloc

Un programma che usa jemalloc può esportare le sue statistiche aggregate con `malloc_stats_print` in modalità JSON. Il [manuale di jemalloc](https://jemalloc.net/jemalloc.3.html) descrive il formato, l'opzione `J` e le possibili differenze temporali dovute alle cache dei thread.

```sh
python3 -B scripts/ressembly-diagnostics.py jemalloc stats.json summary.json
```

L'importatore legge fino a 1 MiB e conserva i contatori validi in byte, le metriche assenti e lo SHA-256 del file sorgente. `examples/jemalloc_stats_lab.c` produce un campione con una normale allocazione e la relativa liberazione. Il modulo gestisce aggregati del processo. La vista interna dell'heap e i collector continuano a usare i profili glibc dichiarati.

## Rivedere una funzione in Ghidra

1. Aggiungere `integrations/ghidra` alle directory dello Script Manager di Ghidra e aprire il proprio programma.
2. Posizionare il cursore in una funzione ed eseguire `RessemblyReview.java`. Scegliere **export** e un nuovo file JSON.
3. Aprire il JSON nel viewer per leggere nome programma, linguaggio, funzione qualificata e hash.
4. Per riprendere la revisione, eseguire lo script in Ghidra, scegliere **open** e indicare il JSON. Lo script confronta hash e linguaggio e risolve un nome univoco nel programma prima di spostare il cursore.

Lo scambio è manuale e riguarda la selezione statica. L'export contiene cinque campi testuali. Hash errati, nomi assenti o ambigui, campi duplicati e file già esistenti sono rifiutati. Il programma aperto resta in lettura. Le API del dialogo e della navigazione sono descritte nella [documentazione di GhidraScript](https://ghidra.re/ghidra_docs/api/ghidra/app/script/GhidraScript.html).

## Collaudi del 21 novembre 2026

| Funzione | Prova eseguita |
|---|---|
| Processi e thread | `spawn` e `fork` su macOS ARM64 e Ubuntu AWS x86-64. Tre PID per sessione, legami padre-figlio, due thread distinti per figlio, ordine locale e uscita pulita. |
| jemalloc | v5.4.0 compilata in una directory temporanea su macOS ARM64. Confrontati i sei contatori importati e lo SHA-256 con l'export reale del programma C. |
| Ghidra | 12.1.4 con JDK 21, in headless. Export e riapertura di un ELF didattico x86-64. Rifiuti verificati per hash diverso, campo duplicato e destinazione già esistente. |
| Windows e ARM64 Linux | Export statico Ghidra del simbolo di prova da un oggetto COFF x86-64 e da un oggetto ELF ARM64 compilati sul Mac. Per i backend restano aperti i collaudi su Windows e Linux ARM64 effettivi. |
| Viewer | Import di una timeline fork reale, della statistica jemalloc e della selezione esportata da Ghidra. Controllate le viste per processo, le coppie di eventi, i dati visualizzati e l'azzeramento. |

I rapporti sono in `work/r11-diagnostics/`. Restano aperti la prova dei dialoghi Ghidra sul desktop, la sincronizzazione continua e il controllo live del debugger nella GUI.

Il pacchetto locale 0.9.0 include il comando `python3 -B scripts/ressembly-diagnostics.py viewer`. Il comando stampa l'indirizzo locale e serve solo le risorse del viewer. La [guida del pacchetto](DIAGNOSTICS-PACKAGE.md) descrive il percorso dall'estrazione al primo rapporto.

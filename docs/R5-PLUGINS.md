# R5 — plugin locali espliciti per annotazioni

Implementazione: `src/ressembly/plugins.py`, `plugin_worker.py`, `plugin_gdb.py`, CLI `scripts/ressembly-plugins.py`, esempio nostro `examples/plugins/summary/`. L'API iniziale accetta dati JSON e restituisce **annotazioni**, separate dalle osservazioni del debugger. Non sono presenti download, marketplace, ricerca automatica nelle directory o esecuzione al caricamento della suite.

## Percorso nel terminale

Dalla radice del progetto:

```sh
python3 scripts/ressembly-plugins.py inspect examples/plugins/summary
python3 scripts/ressembly-plugins.py run examples/plugins/summary snapshot.json --trust-sha256 HASH --output annotations.json
```

Sostituire `HASH` con lo SHA-256 mostrato dall'ispezione, dopo aver letto il codice locale. `snapshot.json` è un oggetto JSON già acquisito; l'esempio conta i registri disponibili e non deduce copertura delle scritture. L'opzione `--output` crea un file nuovo e rifiuta la sovrascrittura. Senza questa opzione il risultato va nel terminale. Nel pacchetto installato gli stessi comandi sono disponibili tramite `ressembly plugins`.

## Uso da GDB

Dopo il caricamento della suite, in una sessione fermata sul proprio programma:

```text
rs-plugin list
rs-plugin inspect /percorso/plugin
rs-plugin load /percorso/plugin HASH
rs-plugin run summary
rs-plugin unload summary
```

`inspect` legge e controlla i file senza eseguirli. `load` registra l'identità e l'hash esplicitamente fornito, senza eseguire il codice. Solo `run` acquisisce un contesto corrente e invoca il plugin; `summary` è l'ID dell'esempio incluso, altri plugin usano il proprio ID. Percorsi contenenti spazi vanno racchiusi tra virgolette.

La fiducia vale per **codice e metadati**: modificare `plugin.py` o versione/manifest dopo `load` provoca il rifiuto al successivo `run`. ID duplicati sono rifiutati finché non vengono scaricati con `unload`. Una nuova sessione GDB parte con registro vuoto; la fiducia non viene salvata globalmente. Non vengono aggiunti callback automatici agli arresti del debugger.

## Contratto API 1

Una directory contiene due file regolari, non collegamenti simbolici:

```json
{"id":"summary","version":"1.0.0","api_version":1}
```

Il manifest `plugin.json` contiene esattamente questi campi. `plugin.py` definisce:

```python
def analyze(snapshot):
    return {
        "api_version": 1,
        "annotations": [{"message": "Nota dell'analista", "address": 4096}]
    }
```

`address` è facoltativo e deve essere un intero unsigned a 64 bit. Il messaggio non vuoto ha massimo 2.048 caratteri; sono ammesse al massimo 128 annotazioni. Campi extra come `observations` o `provenance` dentro l'output del plugin vengono rifiutati: il plugin non può promuovere il risultato a evento acquisito attraverso quel formato.

La risposta accettata ha schema `ressembly.plugin-annotations.v1` e conserva ID/versione/API/hash del plugin, riferimento e hash dello snapshot, provenienza `trusted_local_plugin_output`, stato `annotations_not_debugger_observations`. Queste etichette descrivono la provenienza; non verificano che il contenuto della nota sia vero e non autenticano un file che qualcuno potrebbe modificare successivamente.

## Esecuzione e limiti

Il codice è eseguito in un processo Python separato, con input JSON e una directory temporanea. Il plugin riceve una copia serializzata dello snapshot: modificarla non cambia l'oggetto nel processo del debugger. L'API non fornisce direttamente comandi GDB o un oggetto inferior.

**È codice locale fidato, non una sandbox di sicurezza.** Il processo mantiene i permessi dell'utilizzatore e non è confinato rispetto a filesystem o rete; la separazione non rende sicuro un plugin ostile. L'ispezione e l'hash legano l'autorizzazione ai byte scelti, ma non sostituiscono la revisione del codice. I test di stato invariato riguardano gli esempi nostri eseguiti, non una garanzia contro ogni possibile programma Python.

Budget del runner: manifest 8 KiB, codice 128 KiB, richiesta serializzata complessiva 1 MiB. Timeout standard di 5 secondi, API limitata a un massimo di 10; CPU del worker limitata a 5 secondi. Output/errori catturati sono limitati a 1 MiB per file. Il runner prova a terminare il gruppo dei processi avviato, senza promettere confinamento dei discendenti che si separano volontariamente. Nessun limite di memoria o isolamento del sistema viene dichiarato.

Errore del plugin, JSON invalido, API non supportata, timeout o budget superato producono un fallimento esplicito: nessuna annotazione di quella esecuzione viene accettata. L'invocazione non esegue automaticamente gli input del dossier e non interpreta le annotazioni come sfruttabilità.

## Convalida eseguita

```sh
python3 -m unittest discover -s tests -p test_plugins.py -v
python3 scripts/validate-plugins-linux.py work/plugins-NUOVO
```

Il validatore richiede Linux x86-64 e una directory nuova. Compila un C nostro, usa due processi GDB distinti e conserva comandi, output, codici di uscita, riferimenti e hash. I controlli confrontano registri e 64 byte dello stack mediante primitive GDB prima/dopo il plugin; verificano inoltre che il target non avanzi, che l'ispezione/caricamento non eseguano il plugin, che il digest cambiato sia rifiutato e che il registro non persista nella nuova sessione.

Convalida indipendente Kali effettivamente svolta: `work/kali-lab/plugins-validation/002/validation.json`, **due sessioni GDB e 17 controlli superati**, più **nove test di contratto** superati sia sul Mac sia dentro Kali. Ambiente: Kali 2026.3 x86-64, kernel 7.1.5, GDB 17.2/Python 3.14.7, QEMU TCG sul Mac ARM64. Non è una misura di prestazioni native.

Il primo tentativo `001` è conservato: errore di quoting del Python incorporato nel banco di prova, corretto con stringa raw e controllo sintattico prima dell'esecuzione; nessuna modifica del prodotto necessaria. Una mutazione in copia separata che saltava il confronto con l'hash fidato è stata intercettata (`work/kali-lab/plugins-mutation/`).

Il pacchetto pilota installato su Kali è stato provato separatamente con l'esempio `summary`, osservazioni GDB reali e verifica di integrità finale (`work/kali-lab/installed-pilot003`). Il pilota non attesta il pacchetto finale: le relative prove e le ripetizioni Debian richiedono evidenze separate nel rapporto integrato.

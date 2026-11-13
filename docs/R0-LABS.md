# R0 — corpus di confronto

Programmi nostri in `examples/r0/memory_cases.c`, singolo processo/thread, compilati `-g3 -O0`. Il corpus e il runner sono implementati; la loro presenza non attesta un confronto già eseguito su Linux. Nessun componente è una dipendenza di Ressembly; nessun download automatico, servizio o Daybreak.

| Caso | Controllo good | Caso bad | Aspettativa dal sorgente |
|---|---|---|---|
| buffer | Scrive gli otto byte logici | Scrive dodici byte dentro storage C da sedici | Sentinel logico all'offset 8 cambia solo in bad; **non** è un overflow oltre l'oggetto C e non si pretende che un tool lo diagnostichi |
| uaf | Legge durante la vita e poi libera | Libera e tenta una lettura volatile tramite indirizzo conservato | Uso dopo free intenzionale; valore, crash e riuso non sono specificati. I checkpoint distinguono vita e tentativo, non certificano sfruttabilità |
| pointer | Mantiene puntatore a benign_a | Sostituisce con benign_b | Selezione 1 contro 2; entrambe funzioni innocue nostre, nessun indirizzo controllato esterno |

`rs_checkpoint(label)` espone posizione e regione selezionata. Il runner raccoglie byte della lunghezza dichiarata, backtrace e registri. Non interpreta byte di memoria liberata come oggetto ancora vivo. Il caso UAF bad contiene comportamento indefinito intenzionale e non è un test di correttezza C: nessun valore stale preciso viene imposto come risultato.

## Esecuzione Linux x86-64

Usare un ambiente glibc autorizzato con GDB/Python, compilatore C e Python 3. Ogni directory deve essere nuova. Eseguire da root del progetto:

```sh
python3 scripts/r0/run.py --tool gdb --profile manual --out work/r0-gdb-001
python3 scripts/r0/run.py --tool gef --profile manual --entry /percorso/checkout-gef/gef.py --revision HASH_COMPLETO --out work/r0-gef-001
python3 scripts/r0/run.py --tool pwndbg --profile manual --entry /percorso/checkout-pwndbg/gdbinit.py --revision HASH_COMPLETO --out work/r0-pwndbg-001
```

Gli ultimi due percorsi sono esempi da adattare ai checkout realmente preparati; i tool non vengono installati dal runner. HEAD deve coincidere con la revisione fornita e il checkout dev'essere pulito. Il profilo `manual` è comune ai tre strumenti: watchpoint di scrittura sul sentinel logico `rs_address+8`, watchpoint sullo slot puntatore, read-watchpoint sul byte `rs_address+16` del caso heap. Nel controllo heap è armato mentre l'oggetto è vivo; in UAF bad dopo il checkpoint di free e prima della lettura. Ogni trigger conserva PC al punto di arresto e backtrace: il PC non viene spacciato per istruzione responsabile senza verifica della semantica del watchpoint.

Eseguire separatamente `--profile helper` per GEF e Pwndbg con nuove directory: GEF attiva `heap-analysis-helper`; Pwndbg attiva `track-heap enable`, dopo l'arresto in main. Il profilo helper non aggiunge i watchpoint manuali del confronto comune. Questi comandi e la compatibilità della revisione scelta vanno verificati nel log, non presunti. Ogni sessione usa `gdb -nx`, separando le configurazioni personali e i due concorrenti.

Output: sorgente/binario identificati tramite SHA-256, revisioni/hash loader, compilatore/GDB/host/libc dichiarata, script esatti, sei log e manifest JSON. `wall_seconds` misura il batch compreso avvio debugger: **non** misura il tempo di un analista, non basta per confrontare ergonomia o overhead della sola acquisizione. Il conteggio delle righe dello script non equivale a passaggi manuali. In emulazione dichiarare il backend e non inferire prestazioni hardware.

Il runner salva osservazioni grezze, non PASS diagnostici. `setup_status=setup-error` segnala loader/command non osservato o errori Python/GDB nel log, anche quando GDB ritorna 0; non confrontare queste righe come sessioni diagnostiche valide. `commands-observed` non certifica che l'estensione abbia rilevato un difetto: va revisionato il log. Un tool può arrestarsi su un'anomalia prima dell'ultimo checkpoint: `inferior_exit_observed=false` significa che la sessione non ha osservato exit0, non che il tool è guasto. Il manifest riporta anche exit del debugger e timeout; leggere sempre i log per errori dei comandi, segnali e arresti anticipati. Timeout per sessione: 90 secondi.

## Revisione e gate R0

Confrontare per ciascuno dei sei casi: informazioni già disponibili, punto di arresto, relazione alloc/free, distinzione fra indirizzo e generazione, byte osservati, scritture intermedie non registrate, falsi segnali e azioni manuali necessarie. Annotare versioni e comandi aggiuntivi. Ripetere i compiti con ordine alternato e misurare separatamente il lavoro umano se si vuole affermare un beneficio d'uso. La matrice può concludere che non esiste un vantaggio: nessuna innovazione o superiorità deriva da questo corpus.

Fonti primarie dei comandi, consultate il 13 novembre 2026: [GEF heap helper](https://hugsy.github.io/gef/commands/heap-analysis-helper/) e [Pwndbg track-heap](https://pwndbg.re/stable/commands/linux_libc_elf/track-heap/). Le pagine mobili non certificano la revisione installata.


## Lettura dei trigger e controllo sorgenti dei concorrenti

Nel profilo manuale il read-watchpoint può scattare sia in UAF good sia bad: è lo stato di vita del checkpoint precedente a distinguere i casi, non la presenza del trigger. Non contare il controllo good come vulnerabilità. I watchpoint su sentinel e slot dovrebbero invece mostrare una modifica solo nel rispettivo caso bad, da verificare live.

Ispezione statica dei checkout fissati nel laboratorio (`GEF 809864d00442f9993298e33fd9cd282d687d2f45`, `Pwndbg 9760ac8f1346d142857cffc933995cd6fca34dff`): gli helper UAF usano watchpoint di cambiamento di valore, non `rwatch`. Una lettura UAF può quindi non produrre un loro segnale; inoltre la regione iniziale osservata da GEF non comprende il nostro offset +16. Il test non separa da solo i due limiti. Sono caratteristiche del perimetro da confrontare con le evidenze, non bug attribuiti agli strumenti. GEF dichiara il proprio helper sperimentale. Nel report distinguere capacità documentate, codice ispezionato e risultati eseguiti.

## Compatibilità del runner verificata nel laboratorio

GDB `source` consuma il nome file non quotato; il runner non riusa il quoting del comando `file`. Le prime prove che fallivano su questa differenza sono conservate come pilot, non conteggiate nel confronto valido. I watchpoint manuali vengono disabilitati al checkpoint finale per evitare che il riuso dello stack dopo il ritorno di funzione sembri una modifica durante la vita dell'oggetto.

La revisione Pwndbg fissata segnala un conflitto noto con `commands`/`continue`. Il profilo Pwndbg usa il workaround da essa indicato: `set gdb-workaround-stop-event disabled-deadlock` e `pi gdb.execute("continue")`. I profili con eccezioni/deadlock sono conservati ma esclusi; non si classificano come difetti delle capacità diagnostiche. Questa differenza del flusso è visibile negli script salvati, non nascosta nei tempi.

Risultati effettivi e limitazioni della matrice: [R0-RESULTS.md](R0-RESULTS.md). Per verificare le cinque directory selezionate usare `scripts/r0/verify-results.py` con i cinque percorsi come argomenti; controlla 30 sessioni, checkpoint, campioni e trigger, senza attestare origine o beneficio d'uso.

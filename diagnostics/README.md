# Ressembly Diagnostics 0.9.0

Pacchetto locale GPL-3.0-or-later per la diagnostica di applicazioni e la consultazione di acquisizioni. Occorre Python 3.9 o successivo. Ghidra serve solo per lo scambio di selezioni statiche.

Scarica il [pacchetto ZIP](downloads/ressembly-diagnostics-0.9.0-local.zip) e controlla il [checksum SHA-256](SHA256SUMS). Estrai lo ZIP e apri un terminale nella cartella estratta. Il [rapporto pubblico](VALIDATION.md) riassume le prove.

```sh
python3 -B scripts/ressembly-diagnostics.py demo processes.json
python3 -B scripts/ressembly-diagnostics.py viewer
```

Apri l'indirizzo indicato dal secondo comando e seleziona `processes.json`. Il viewer ascolta solo su `127.0.0.1`. I file importati restano nel browser. Premi Ctrl+C nel terminale per chiudere il viewer.

Per registrare il percorso con fork su un sistema che lo supporta, usa `demo fork.json --method fork`. Per importare le statistiche JSON di jemalloc usa `jemalloc stats.json summary.json`. Entrambi i comandi vogliono un percorso di output nuovo.

La [guida](docs/DIAGNOSTICS.md) descrive gli eventi cooperativi, le statistiche aggregate e lo script Ghidra. I comandi sono stati verificati su macOS ARM64 e Linux x86-64 nel perimetro dei rapporti. L'uso su Windows o Linux ARM64 richiede una prova sul sistema effettivo.

Il pacchetto comprende la timeline cooperativa, il riepilogo jemalloc, lo scambio manuale di selezioni Ghidra e il viewer. I backend debugger e la raccolta heap concorrente rimangono attività separate della suite.

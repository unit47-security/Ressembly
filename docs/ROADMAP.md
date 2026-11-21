# Ressembly — roadmap operativa

Aggiornata il 21 novembre 2026. Fonte corrente per il progetto UNIT-47; [roadmap Windows/Qt v0.1](ROADMAP-WINDOWS-v0.1.md) conservata come storico.

## Consegna Diagnostics 0.9.0

| Stato | Attività | Risultato |
|---|---|---|
| ✅ | Processi e thread cooperanti | Timeline con spawn e fork collaudata su macOS ARM64 e Ubuntu x86-64. |
| ✅ | Statistiche jemalloc | Sei contatori aggregati verificati su un export reale della 5.4.0. |
| ✅ | Selezioni statiche Ghidra | Export e riapertura collaudati in headless. |
| ✅ | Viewer locale | Import e navigazione dei rapporti nel browser. |
| 🟡 | Funzioni estese | Restano aperti cronologia heap concorrente, tracciamento di processi arbitrari, dialoghi desktop Ghidra, sincronizzazione continua, controllo live del debugger e backend Windows/Linux ARM64. |
| ⬜ | Suite 1.0 | Perimetro e collaudi finali ancora aperti. |

[Pacchetto ZIP](../diagnostics/downloads/ressembly-diagnostics-0.9.0-local.zip) · [Guida](../diagnostics/README.md) · [Collaudi](../diagnostics/VALIDATION.md)

Le sezioni successive documentano le fasi della suite e il perimetro dell’alfa 0.6.0.

## Obiettivo e vincoli

Suite modulare di reverse engineering e ricerca sulle vulnerabilità su Linux x86-64, GDB/Python e terminale. La cronologia degli oggetti è uno dei moduli, non l'intero prodotto. Nessuna dipendenza Daybreak, GEF/Pwndbg, servizio a pagamento o IA obbligatoria. Windows, LLDB, altre architetture e GUI restano successive opzioni. FaultCore mantiene riproduzione/minimizzazione dei crash; LOLDEX resta esterno a UNIT-47.

## Numerazione e stato verificato

La richiesta “fino alla fase 3 inclusa” comprende **tutto R3a–R3e**. La vecchia corrispondenza informale fase 1=R1, fase 2=R0, fase 3=R2 non rappresentava tutto il lavoro richiesto: è ritirata. **R0, R1, R2 e R3 sono ora convalidati nel perimetro dichiarato.** Risultati, ripetizioni indipendenti, correzioni e limiti: [rapporto finale](PHASES-1-3.md).

| Fase | Consegna | Gate verificato / stato |
|---|---|---|
| R0 | Confronto pratico GDB/GEF/Pwndbg | 30 sessioni + 30 indipendenti; conclusioni circoscritte, nessuna superiorità dimostrata |
| R1a/R1b | Acquisizione marker e affidabilità | 16 + 16 prove reali; altre 16 di regressione dopo R3 |
| R2a | malloc/free selettivi, identità e riuso | Convalidata insieme a R2b; fallimenti, ritorni mancanti e limiti espliciti |
| R2b | Una regione osservata con watchpoint | 22 + 22 prove, oracolo separato, smoke ampiezze; altre 22 di regressione dopo R3 |
| R3a | Assembly, breakpoint, registri, stack | Convalidata con GDB e target con/senza simboli; dati indisponibili espliciti |
| R3b | Mappe, permessi, dump, ricerca, puntatori | Convalidata con limiti, PROT_NONE, cicli/null, dati aggiornati; replay indipendente |
| R3c | Vista strutturale heap | 13 + 13 sessioni; glibc 2.36/tipi di debug, una arena/thread; quattro casi extra |
| R3d | Pattern, offset, proprietà ELF | 44 + 44 controlli, confronto readelf; altri 18 controlli indipendenti |
| R3e | Dossier persistenti | 14 + 14 controlli, riapertura da revisore separato, build/run coerenti, export e confronti |
| Integrazione | Moduli R3 con collector R2 attivo | Due percorsi × 20 controlli GDB + ripetizione indipendente; nessuna fusione silenziosa delle identità |
| **R4** | **Alfa UNIT-47 locale installabile** | Implementata, GPL-3.0-or-later, prova utente positiva; dossier finali separati |
| R5 | Cronologia estesa, Ghidra offline, plugin locali | Implementati e convalidati nel perimetro del rapporto R4/R5 |

Ambiente convalidato R1/R2/R3: Debian 12 x86-64 emulato QEMU TCG sul Mac ARM64, GDB 13.1/Python 3.11.2, glibc 2.36. R0 usa un runtime GDB comune separato documentato. Questa matrice storica non attestava Kali; R4 aggiunge il collaudo Kali limitato descritto sotto. Hardware nativo e prestazioni fisiche non verificati. Il prototipo HTML rimane separato, offline e sintetico.

## R4/R5 — perimetro completato

[Rapporto integrato e dossier](PHASES-4-5.md). Pacchetto locale deterministico e installazione pulita; Debian per i profili glibc 2.36; Kali corrente per moduli generali con rifiuto esplicito dei profili allocator incompatibili. Prova umana riferita positiva, licenza scelta dall'utente. R5 include calloc/realloc, quattro regioni selettive, identità build/file offset verso Ghidra e plugin di annotazione esplicitamente fidati. Non è una registrazione completa delle scritture.

## R6 — profilo glibc 2.43 implementato

[Rapporto R6](R6.md): collector e vista heap sul build Kali glibc 2.43-4, profili/layout espliciti, corpus con oracoli separati, regressione del target 2.36 in sysroot corrispondente e pacchetto locale 0.6.0. Stato conclusivo installazione/pulizia: `work/r6-gates/acceptance.json`. Un solo laboratorio temporaneo, picco inferiore a 3 GB, poi rimozione dei file voluminosi. Nessun caricamento su GitHub eseguito.

## Seguito proposto, non avviato

Prima prova prolungata su hardware Linux x86-64 fisico, con costi e usabilità misurati. Successivamente scegliere separatamente attach/fork, multithread o nuovi allocator. GUI, Windows/LLDB e altre architetture rimangono possibilità future. La pubblicazione iniziale può essere una alfa con il perimetro dichiarato, previa decisione esplicita del proprietario; non richiede fingere che queste estensioni siano già presenti.

## Regola di avanzamento

Una fase si chiude con codice, percorso ripetibile, risultati conservati, revisione e limiti dichiarati. Test sul Mac e fixture non attestano funzionamento Linux. Un evento allocator non attesta una scrittura; una differenza tra snapshot non ricostruisce gli accessi intermedi; nessun singolo segnale dimostra sfruttabilità. Le versioni supportate sono quelle effettivamente collaudate.

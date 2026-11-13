# Ressembly — suite di reverse engineering UNIT-47

Decisione del 24 ottobre 2026. Stato del 13 novembre: **R0, R1, R2 e R3a–R3e implementati e convalidati nel laboratorio Debian x86-64 emulato**. R4 e R5 sono ora implementati nel perimetro del [rapporto R4/R5](PHASES-4-5.md): pacchetto locale GPL-3.0-or-later, cronologia estesa, Ghidra e plugin. R6 estende i profili allocator al build Kali glibc 2.43-4, con [prove e limiti](R6.md); nessuna pubblicazione o prova hardware nativa. [Rapporto completo](PHASES-1-3.md).

## Identità e obiettivo

Ressembly è una suite modulare destinata alla distribuzione da parte di UNIT-47, per reverse engineering, ricerca sulle vulnerabilità ed exploit development in laboratori e attività autorizzate.

L'obiettivo è offrire un ambiente di lavoro completo e coerente. GEF e Pwndbg sono riferimenti e termini di confronto. Una superiorità rispetto a questi strumenti deve essere misurata, non dichiarata in anticipo. La prima funzione distintiva da valutare è ricostruire la vita degli oggetti in memoria con riferimenti alle osservazioni raccolte.

Questa decisione sostituisce la precedente direzione Windows-first C++/Qt e la riduzione del prodotto a un solo strumento di confronto fra esecuzioni. Il prototipo HTML esistente resta un esperimento offline; non è la suite né una sua integrazione funzionante con GDB.

## Architettura proposta

- Motore iniziale: GDB su Linux x86-64, con Kali come ambiente di distribuzione da verificare.
- Adattatore: estensione Python che raccoglie dati tramite le API del debugger.
- Nucleo indipendente dal debugger: identità degli oggetti, validazione, eventi, confronti ed esportazione; testabile offline.
- Interfaccia iniziale: comandi nel terminale, contesto leggibile e navigazione delle evidenze.
- Moduli separati con contratti espliciti, per aggiungere analisi senza riscrivere il nucleo.
- Nessuna dipendenza obbligatoria da GEF; eventuale coesistenza deve essere collaudata, non presunta.

Windows, altri debugger, altre architetture e un'interfaccia grafica restano estensioni successive da valutare. La prima versione non dipende da un servizio web o da un modello IA.

## Componenti della suite

| Componente previsto | Responsabilità |
|---|---|
| Contesto di debugging | Assembly, registri, stack, mappe e posizioni correnti |
| Esplorazione della memoria | Regioni selezionate, ricerca, puntatori e annotazioni |
| Vita degli oggetti | Allocazioni, liberazioni, riutilizzi e accessi effettivamente osservati |
| Esperimenti | Input, ambiente, snapshot, confronti, note e riferimenti |
| Estensioni | Adattatori e moduli con versioni e capacità dichiarate |

I moduli iniziali fino a R3 sono disponibili nei limiti di [R3.md](R3.md); estensioni e copertura generale restano future.

## Primo esperimento tecnico

Su un programma C nostro, Linux x86-64, processo e thread singoli, allocator glibc e versioni dichiarate:

1. Osservare un insieme esplicito di operazioni di allocazione e liberazione.
2. Assegnare una nuova identità a ogni allocazione: lo stesso indirizzo riutilizzato non identifica lo stesso oggetto.
3. Selezionare un oggetto e una porzione limitata da osservare.
4. Registrare gli accessi intercettati con posizione del codice e contesto disponibile.
5. Mostrare una cronologia leggibile insieme ai limiti di acquisizione.

Non si presume che un hook sull'allocator catturi le scritture. I watchpoint hanno limiti di numero e dimensione: la copertura effettiva deve essere esplicita. Le scritture non registrate restano ignote. Una futura strumentazione più ampia richiederà misure di overhead e una scelta separata del backend.

Ogni evento deve conservare almeno identità del target/build, esecuzione, ordine di acquisizione, thread, tipo, oggetto interessato, indirizzo grezzo, posizione del codice se nota e provenienza. L'identità modulo/offset aiuta a confrontare posizioni del codice; non rende automaticamente confrontabili puntatori heap o stack fra esecuzioni.

Un accesso osservato dopo una liberazione è un elemento da esaminare considerando eventuali riallocazioni; non dimostra da solo la sfruttabilità. L'assenza di un evento non dimostra l'assenza di un accesso.

## Traguardi e criteri di accettazione

La fonte operativa corrente è [ROADMAP.md](ROADMAP.md), aggiornata il 13 novembre 2026, con risultati attesi, dipendenze, ambiente e prove di completamento. [BACKLOG.md](BACKLOG.md) traduce le fasi in piccoli task; [VERIFICA.md](VERIFICA.md) registra solo le verifiche realmente eseguite.

- **R0:** confronto pratico degli strumenti; la ricognizione documentale non lo completa.
- **R1:** nucleo e acquisizione minima; R1a/R1b sono convalidate nel laboratorio emulato; affidabilità e casi negativi hanno dossier e replay indipendente.
- **R2:** tracciamento selettivo malloc/free e regione osservata, separando eventi allocator e cambiamenti realmente intercettati.
- **R3:** contesto debugger, esplorazione memoria, heap dichiarato, strumenti exploit-lab ed esperimenti persistenti: tutti convalidati nel perimetro iniziale dichiarato, inclusa integrazione e revisione indipendente.
- **R4:** alfa locale installabile UNIT-47 con compatibilità e licenza esplicite; pubblicazione solo su richiesta.
- **R5:** cronologia calloc/realloc e quattro regioni, Ghidra offline e plugin locali fidati; implementati con limiti espliciti.
- **R6:** profilo allocator glibc 2.43, layout e ritorni specifici, regressione 2.36 e laboratorio temporaneo entro 3 GB.

La roadmap corrente conserva i gate di riuso indirizzi, letture mancanti, interruzione, risorse limitate, compatibilità e revisione delle conclusioni. Le stime sono budget preliminari, non date promesse.

## Relazione con gli altri progetti

FaultCore mantiene riproduzione e minimizzazione dei crash. Ressembly studia l'esecuzione e la memoria durante l'analisi. RoleDiff mantiene il confronto delle autorizzazioni. LOLDEX resta esterno a UNIT-47. Eventuali scambi di dati richiedono contratti verificabili, non accorpamenti automatici dei progetti.

## Stato verificabile

Il prototipo HTML resta offline e sintetico. Il backend GDB/Python operativo comprende i moduli R1/R2/R3, indipendenti da GEF/Pwndbg e senza Daybreak. [PHASES-1-3.md](PHASES-1-3.md) registra prove reali e limiti; [R3.md](R3.md) fornisce il percorso d'uso. L'adattatore marker R1 rimane una prova storica separata; la cronologia R2 intercetta malloc/free selettive senza marker allocator. Il loader suite integra i moduli correnti e conserva gli eventi allocator separati dai cambiamenti di valore realmente osservati.

La precedente corrispondenza informale “fase 3 = R2” era incompleta rispetto alla richiesta. La chiusura corrente include tutto R3a–R3e. Il rapporto storico non attestava Kali; la matrice R4/R5 lo aggiunge limitatamente ai moduli generali. Non attesta una suite matura, superiorità o hardware nativo. R4/R5 hanno evidenze e limiti separati e la pubblicazione non è autorizzata implicitamente.

## Fonti di confronto iniziali

- Pwndbg: https://github.com/pwndbg/pwndbg e https://github.com/pwndbg/pwndbg/releases
- GEF: https://github.com/hugsy/gef
- Tenet: https://github.com/gaasedelen/tenet
- Ghidra Debugger: https://ghidra.re/ghidra_docs/GhidraClass/Debugger/A6-MemoryMap.html

Le fonti identificano strumenti e capacità da confrontare; non costituiscono una validazione della domanda di mercato.

> Stato operativo corrente: R1a e gate Linux in [R1A.md](R1A.md); audit in [AUDIT-2026-10-24.md](AUDIT-2026-10-24.md). Il seguito conserva il piano storico.

> Documento storico v0.1: la direzione corrente approvata il 24 ottobre 2026 è in [SUITE-UNIT47.md](SUITE-UNIT47.md). Il piano Windows/C++/Qt qui descritto è superato.

# Ressembly — backlog operativo

24 ottobre 2026. I task seguenti non sono già implementati, salvo le basi M0 descritte nel README.

## RS-000 — shell desktop Windows x64

Creare applicazione C++/Qt con importazione osservazioni, elenco funzioni, dettaglio evidenze e notebook. GUI nativa, senza browser incorporato o servizio HTTP. Operazioni lunghe fuori dal thread UI. Riutilizzare il corpus M0 come contratto di comportamento, senza dichiarare il motore JavaScript già convertito.

Accettazione: build Windows riproducibile, importazione del bundle dimostrativo, qualità parziale visibile, finestra reattiva e limiti di memoria documentati. Sul Mac si può preparare il codice, ma il gate Windows richiede una build e una prova reali.

## RS-001 — contratto acquisizioni v1

Aggiungere documento JSON Schema versionato e validatore del contratto completo: hash input, identità acquisizione, configurazione, ambito, produttore, architettura e qualità. Differenziare metadati dichiarati da verifiche indipendenti. Esempi validi e invalidi; rifiuto esplicito degli schemi sconosciuti. Nessun avvio di target.

Accettazione: corpus di input malformati, limiti di dimensione prima dell'allocazione, test di build diverse, capture scope diverso, frame/thread non attribuibili, dati persi. Diagnostica leggibile e nessuna normalizzazione arbitraria dei numeri.

## RS-002 — corpus reale portabile

Tre sorgenti C/C++ piccoli, input e risultati dichiarati. Build riproducibile in Windows x64 con simboli e senza simboli. Manifest degli hash e compilatore. Nessun crash intenzionale richiesto. Il comportamento può essere verificato dal sorgente solo dopo che l'analista ha completato il compito.

Accettazione: input controllati producono almeno due comportamenti distinguibili e un controesempio. Source instrumentation, breakpoint sampling e instruction tracing hanno provenienze differenti, non interscambiabili.

## RS-003 — spike collector x64dbg

Plugin minimo con un punto di ingresso selezionato, raccolta esplicita e arresto. Copiare i dati nel callback e scaricarli fuori dal thread del debugger. Nessuna elaborazione pesante o puntatore conservato fuori validità. Buffer limitato; overflow produce dropped events e qualità parziale.

Accettazione: confronto manuale di moduli/RVA/thread con x64dbg; stop, detach e target che termina non bloccano il debugger. Non dichiarare completa l'osservazione di sole funzioni selezionate rispetto all'intero processo. Richiede ambiente Windows x64.

## RS-004 — vertical slice con osservazioni reali

Importare un bundle del collector e renderlo nel visualizzatore. Aggiungere identificatore del sorgente a ogni riga; esportare note e riferimenti senza riscrivere il bundle originale. Se cambia una selezione, una nota conserva il proprio esperimento e non migra sul confronto sbagliato.

Accettazione: percorso da acquisizione a dossier ripetibile da un secondo utilizzatore. Tutte le righe hanno un'origine esistente; tracce incomplete restano incomplete anche dopo export/import.

## RS-005 — collegamento a esportazione Ghidra

Importazione offline di metadati di una sola build. Hash e architettura obbligatori, RVA normalizzato, collisioni esplicite, nessun matching per nome soltanto. Nessuna importazione del motore di decompilazione nel visualizzatore.

Accettazione: moduli a basi diverse si associano correttamente; stesso nome in DLL diverse resta distinto; una build aggiornata viene rifiutata.

## RS-006 — prova di utilità

Preparare compiti, ordine bilanciato e modulo di misura. Raccogliere consenso e autorizzazione prima di contattare utenti. Misurare il lavoro con e senza notebook, distinguendo familiarità con il compito e beneficio del tool. Scrivere un breve rapporto che può anche concludere che il prodotto non offre vantaggi.

## Sequenza

RS-000, RS-001 e progettazione RS-002 → RS-003 su Windows → RS-004 → RS-005 → RS-006. Nessuna pubblicazione o lavoro notturno autonomo è stato avviato.

> Documento storico v0.1: la direzione corrente approvata il 24 ottobre 2026 è in [SUITE-UNIT47.md](SUITE-UNIT47.md). Il piano Windows/C++/Qt qui descritto è superato.

# Ressembly — specifica iniziale v0.1

Data: 24 ottobre 2026. Direzione tecnica proposta e prototipo M0; nessuna promessa di supporto già operativo ai debugger.

## Decisione di prodotto

Un’app desktop Windows in C++ con Qt per il ricercatore che vuole comprendere una funzione del software osservandola in esperimenti controllati. L'interfaccia richiama la leggibilità di OllyDbg; il lavoro è organizzato intorno a domande, osservazioni e ipotesi, non soltanto intorno agli indirizzi.

Domanda iniziale: «Quale codice partecipa alla decodifica di questo formato?»

Percorso: registrazione dell'esperimento A → azione B con una variazione dichiarata → acquisizioni confrontabili → funzioni osservate solo in B → ispezione nel debugger e in Ghidra → terzo esperimento per cercare un controesempio → nota con riferimenti agli eventi.

Il confronto produce candidati da esaminare. L'analista resta responsabile dell'interpretazione. Un evento aggiuntivo, una frequenza differente o una coincidenza non dimostrano la funzione semantica né la causalità.

## Utilizzatore e primo laboratorio

Ricercatori e sviluppatori che lavorano su programmi nativi propri, open source o autorizzati. Primo laboratorio operativo previsto: Windows x64, modalità utente, processo singolo e stesso binario. La lettura offline delle osservazioni resta utilizzabile anche dal Mac.

Programmi piccoli con comportamenti normali: lettura di un'intestazione, decodifica di un'immagine e selezione di un algoritmo. FaultCore mantiene la gestione dei crash e della riduzione degli input; Ressembly non la reimplementa.

## Funzioni MVP previste

1. Creare un esperimento: domanda, input, azione, ambiente e finestra di osservazione.
2. Raccogliere osservazioni tramite un adattatore x64dbg: iniziamente snapshot a breakpoint e punti di ingresso selezionati.
3. Conservare binario/build, hash dei moduli, RVA, thread, evento e provenienza. Non correlare indirizzi assoluti fra esecuzioni.
4. Confrontare una build e un ambito di acquisizione identici. Esplicitare copertura, perdite e porzioni non osservate.
5. Rinominare e annotare le funzioni nel notebook senza sovrascrivere l'evidenza originale.
6. Collegare osservazioni e posizioni statiche di Ghidra con controllo di hash e base immagine.
7. Esportare un dossier leggibile con riferimenti verificabili, ipotesi, controesempi e limiti.

## Cosa implementa M0

Il prototipo confronta inventari di ingressi funzione. Non ricostruisce istruzioni, stack delle chiamate, durate o relazioni causali. Il tipo `function_entry` è un contratto interno proposto, non una dichiarazione di compatibilità con un formato nativo esistente.

L'identità di una posizione è SHA-256 del modulo + RVA normalizzato. Il nome della funzione è solo una descrizione. L'hash del binario di riferimento deve coincidere nelle due osservazioni e nell'intestazione del bundle. Un modulo differente resta un'identità distinta: non viene eseguito matching tra versioni.

`complete` è una dichiarazione del produttore. L'interfaccia la chiama completezza dichiarata, non osservazione universale. Il confronto non attesta che un esportatore sia attendibile. Una traccia parziale conserva la qualità parziale e non permette inferenze di non-esecuzione.

I numeri di sequenza sono ordine di acquisizione, non un ordine causale globale tra thread. I conteggi sono eventi, non tempo CPU o istruzioni. La normalizzazione non rimuove valori arbitrari per far coincidere le osservazioni.

## Architettura scelta

```text
Adattatore x64dbg (C++, da implementare)
   ↓ eventi copiati, coda limitata, nessuna elaborazione pesante nei callback
Formato di osservazione versionato + identità del target
   ↓
Motore offline: validazione → normalizzazione → confronto → riferimenti
   ↓
App desktop C++/Qt: esperimenti | assembly | registri | memoria | evidenze | notebook
   ↔ adattatore Ghidra (da implementare, matching esatto)
```

M0 usa JavaScript senza dipendenze e HTML locale soltanto per l’anteprima. Il prodotto previsto è un’applicazione desktop Windows x64 in C++/Qt, distribuita come eseguibile e senza server web. Il core C++ dovrà essere implementato e verificato sul medesimo corpus. Un futuro lettore offline macOS non implica debugging Windows dal Mac.

Per il primo collegamento operativo si usa il debugger esistente attraverso un plugin, senza riscrivere il motore Windows. L'integrazione è opzionale e separata. REA/ReAgent restano strumenti complementari; non sono dipendenze di M0 e non costituiscono un'integrazione già disponibile.

## Prestazioni e dati

M0: massimo 20 osservazioni, 50000 eventi per bundle e 256 moduli per osservazione; importazione UI fino a 5 MB. Questi limiti definiscono un prototipo, non un benchmark di produzione. Dati grandi richiederanno streaming, paginazione e worker senza bloccare l'interfaccia.

L'adattatore futuro dovrà dichiarare eventi persi, buffer esauriti, cancellazione e disconnessione. Un'acquisizione interrotta non diventa completa. I callback non devono conservare puntatori del debugger dopo la loro validità.

Il visualizzatore non interpreta i dati importati come HTML o comandi. L'importazione non avvia processi. L'esportazione contiene input dichiarati e note: sono dati di ricerca da gestire secondo l'ambiente dell'utente. Nessun servizio cloud necessario.

## Esclusioni fino al superamento dell'MVP

Kernel, driver, multiprocesso, replay deterministico, backtracking universale, ricostruzione automatica dei tipi, taint tracking completo, ricostruzione semantica tra versioni, rilevamento automatico di vulnerabilità, patch del programma e agente IA autonomo.

Non includere una funzione solo perché appariscente: deve ridurre il lavoro di un esperimento reale, preservando le evidenze.

## Criterio di validazione del prodotto

Confrontare il notebook con il normale uso di x64dbg/Ghidra su tre piccoli bersagli e coinvolgere almeno cinque utilizzatori. Misurare tempo alla prima ipotesi corretta, tempo alla verifica, errori di interpretazione e capacità di riprendere il lavoro dopo un giorno.

Un vantaggio proposto è ridurre almeno del 25% il tempo mediano su due dei tre compiti senza aumentare le conclusioni errate. È un gate progettuale da misurare, non un risultato osservato. Se non emerge un vantaggio, restringere il prodotto a plugin/notebook oppure interrompere l'idea di debugger autonomo.

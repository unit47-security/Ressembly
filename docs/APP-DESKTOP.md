> Documento storico v0.1: la direzione corrente approvata il 24 ottobre 2026 è in [SUITE-UNIT47.md](SUITE-UNIT47.md). Il piano Windows/C++/Qt qui descritto è superato.

# Ressembly — applicazione desktop

Decisione del 24 ottobre 2026: il prodotto è un’app Windows x64 in C++ con Qt. L’HTML consegnato è un’anteprima temporanea dell’esperienza, non un sito web né il prodotto finale.

## Componenti

- **Ressembly.exe**: finestra desktop, gestione esperimenti, visualizzazione delle evidenze, notebook ed esportazione.
- **Core C++**: identità del binario/moduli, validazione osservazioni, normalizzazione RVA, confronto e riferimenti. Deve riprodurre i risultati del corpus M0; non è implementato oggi.
- **Adattatore x64dbg**: plugin separato per gli eventi e i comandi effettivamente supportati. Prima versione limitata a punti di osservazione selezionati. Non sostituisce il motore del debugger.
- **Adattatore Ghidra**: associazione di metadati statici alla build esatta. Previsto dopo il collector; non già collegato.

## Primo percorso nativo

La prima shell apre file di osservazioni locali e consente analisi offline. Solo dopo il superamento dei test viene aggiunta una connessione esplicita al collector Windows. Nessun listener HTTP è necessario. Un eventuale canale IPC deve essere locale, limitato alla sessione e con controllo dell’identità del processo; non è presente nel prototipo.

## Schermata prevista

1. Esperimenti e input a sinistra.
2. Funzioni e assembly al centro, con provenienza delle informazioni.
3. Registri, memoria e stack soltanto quando effettivamente acquisiti dal debugger.
4. Evidenze e annotazioni collegate all’esperimento.
5. Confronto fra osservazioni dello stesso binario, evitando indirizzi assoluti e corrispondenze per nome soltanto.

Un pannello senza dati mostra «non acquisito», non registri o assembly inventati. I pulsanti di esecuzione saranno attivati soltanto con un backend vivo e verificato.

## Sviluppo e verifica

Qt/C++ permette di organizzare una GUI desktop, ma non rende intercambiabili i motori di debugging fra sistemi operativi. La prima versione operativa richiede Windows x64. Una futura applicazione macOS potrà leggere dossier ed esportazioni; il debugging nativo macOS richiederebbe un adattatore distinto.

Oggi sono consegnati progetto, contratto iniziale, anteprima e motore di confronto JavaScript. Non esistono ancora una build .exe, un plugin x64dbg o una sessione live verificata.

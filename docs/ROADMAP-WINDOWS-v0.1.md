> Stato operativo corrente: R1a e gate Linux in [R1A.md](R1A.md); audit in [AUDIT-2026-10-24.md](AUDIT-2026-10-24.md). Il seguito conserva il piano storico.

> Documento storico v0.1: la direzione corrente approvata il 24 ottobre 2026 è in [SUITE-UNIT47.md](SUITE-UNIT47.md). Il piano Windows/C++/Qt qui descritto è superato.

# Ressembly — roadmap v0.1

24 ottobre 2026. Piano di sviluppo con gate, non calendario garantito. Ipotesi per stimare: uno sviluppatore esperto che lavora con continuità, accesso a Windows x64 per i test nativi e tempo dedicato alla revisione. Lo studio del reversing e gli altri progetti allungano i tempi.

## M0 — direzione e prototipo offline

Consegnato: specifica, confronto degli strumenti, notebook visivo, confronto di ingressi funzione, filtri, importazione JSON ed esportazione con note. Dati sintetici chiaramente dichiarati. 14 test del motore. La verifica visiva è registrata in VERIFICA.md.

Non è consegnato un debugger Windows. Nessuna acquisizione dal vivo, replay o integrazione Ghidra già funzionante.

## M1 — shell desktop, contratto stabile e corpus reale (stima 1–2 settimane)

- Creare una prima shell nativa C++/Qt su Windows x64 che importa osservazioni offline; nessun browser incorporato richiesto.
- Versionare il formato delle osservazioni con campi obbligatori, limiti e regole sui dati ignoti.
- Aggiungere hash di input, configurazione dell'acquisizione, tool/build e ambiente reale.
- Creare tre piccoli programmi C/C++ innocui: parser di intestazione, selezione di formato e decodifica semplice.
- Compilarli con e senza simboli; raccogliere osservazioni ripetute con collector esplicito.
- Testare ASLR, moduli diversi, input identici, registrazioni parziali, nomi ambigui e modifiche della configurazione.

Gate: un bundle realmente raccolto percorre importazione → confronto → nota → esportazione. La ricostruzione non inventa l'identità del binario né la completezza; importazioni incompatibili sono rifiutate con motivo leggibile.

## M2 — collector x64dbg Windows x64 (stima 2–4 settimane)

- Plugin C++ per processo utente singolo; attivazione esplicita da parte dell'analista.
- Prima modalità: un insieme dichiarato di breakpoint su ingressi di funzione selezionati.
- Copiare soltanto dati validi nel callback; inviarli a una coda limitata gestita da worker.
- Salvare load/unload dei moduli, base immagine, RVA, thread e riferimenti agli eventi.
- Esporre stato di raccolta e budget; registrare perdite, annullamento e disconnessioni.
- Non affermare che un breakpoint su poche funzioni sia una traccia completa del programma.

Gate: almeno 20 acquisizioni su piccoli bersagli Windows x64; identità e indirizzi verificati contro il debugger, nessun blocco dell'interfaccia, qualità parziale preservata sui casi interrotti. Misurare overhead e volume in un ambiente dichiarato. Questa fase richiede Windows nativo/compatibile; il Mac da solo non ne attesta il risultato.

## M3 — notebook persistente e ricerca per esperimenti (stima 2–3 settimane)

- Esperimenti con domanda, azione, input, controlli e ambiente.
- Ipotesi collegata a posizioni ed eventi, separata dai fatti acquisiti.
- Stati dell'ipotesi: proposta, sostenuta nel campione, controesempio trovato, inconcludente. Nessun verdetto automatico dal solo diff.
- Controesempi espliciti e ripetizioni; salvare osservazioni discordanti.
- Ricerca fra funzioni, input e note; navigazione al riferimento originale.
- Sessioni recuperabili senza riscrivere i dati raccolti.

Gate: un collega riprende un esperimento da un dossier e ritrova tutti i riferimenti; nessuna nota orfana dopo aggiornamento o importazione.

## M4 — collegamento statico a Ghidra (stima 2–3 settimane)

- Importare nomi, firme e indirizzi di funzione da un'esportazione dichiarata.
- Verificare hash, architettura, modulo e immagine base prima di collegare un evento.
- Matching esatto per build; offset ambigui restano irrisolti.
- Separare pseudocodice inferito, annotazioni dell'analista e dati runtime.
- Aprire una posizione corrispondente nell'ambiente compatibile; versioni e limiti espliciti.

Gate: matching corretto sul corpus con e senza simboli e rifiuto dei binari sostituiti. L'assenza di una funzione nei risultati Ghidra non viene interpretata come non-esecuzione.

## M5 — confronto con il lavoro reale (stima 2–3 settimane)

Cinque utilizzatori, tre compiti: individuare il parser, distinguere due modalità e verificare un'ipotesi con un controesempio. Confronto con x64dbg + Ghidra e con i tool già usati dall'analista.

Misurare tempi, errori, passaggi manuali e qualità del dossier. Il numero di funzioni evidenziate non è una metrica di utilità.

Gate proposto: riduzione del tempo mediano almeno del 25% su due compiti, senza aumento delle conclusioni errate. Se il vantaggio non emerge, migliorare il notebook o restare plugin; non proseguire automaticamente verso un nuovo debugger completo.

## M6 — distribuzione alfa (stima 2–4 settimane dopo i gate precedenti)

Packaging riproducibile, installazione documentata, limiti del collector, gestione di tracce grandi, accessibilità, esportazioni portabili, documentazione di esempi e compatibilità verificata delle versioni. Rilasciare soltanto capacità collaudate.

Gate: nuova macchina Windows completa il percorso documentato, un utente riconosce una raccolta parziale e il programma resta reattivo con il corpus di riferimento.

## Dopo l'alfa: scegliere una sola estensione

- Migliore associazione fra comportamenti e funzioni con esperimenti ripetuti.
- Formati di traccia ulteriori con adattatori indipendenti.
- Supporto Linux o ARM64 dopo misure e richiesta concreta.
- Miglioramento della shell desktop C++/Qt sulla base delle misure di utilizzo.

Il supporto IA resta facoltativo e successivo: eventuali spiegazioni devono citare osservazioni, distinguere ipotesi e non controllare automaticamente processi. FaultCore resta responsabile della pipeline crash/minimizzazione; nessuna duplicazione.

## Impegno complessivo

L'ordine di grandezza delle stime sopra è 11–19 settimane dopo M0 per una prima alfa stretta, con competenze e ambiente già disponibili. Non è una promessa di prodotto maturo in quel periodo. Un principiante che studia e porta avanti altri progetti deve pianificare un percorso più lungo e rivalutare ogni milestone.

# Ressembly — backlog corrente

13 novembre 2026. La [roadmap](ROADMAP.md) usa R0–R5 senza la precedente ambigua corrispondenza informale. Chiusura fino a R3: [rapporto con evidenze](PHASES-1-3.md). Il [backlog Windows v0.1](BACKLOG-WINDOWS-v0.1.md) resta storico.

| ID | Fase | Attività | Stato |
|---|---|---|---|
| LIN-001 | R1a | Laboratorio Linux x86-64 e versioni | Convalidato in Debian x86-64 emulato |
| LIN-002 | R1a | Acquisizione C, marker e byte verificati | Convalidato, oracolo e replay indipendente |
| LIN-003 | R0 | Tre laboratori con controlli | Convalidato |
| LIN-004 | R0 | Confronto GDB/GEF/Pwndbg | 30 + 30 sessioni convalidate |
| LIN-005 | R1b | Interruzioni, errori, budget, uscita e nuovo run | Convalidato; regressione post-R3 superata |
| LIN-006 | R1b | Metadati, hash, file incompleti | Convalidato; coerenza non equivale ad autenticità |
| LIN-007 | R2a | malloc/free e generazioni | Convalidato nel perimetro selettivo |
| LIN-008 | R2b | Regione hardware, risorse e costo | Convalidato; regressione post-R3 superata |
| LIN-009 | R3a | Contesto debugger | Convalidato con/senza simboli, replay indipendente |
| LIN-010 | R3b | Mappe, ricerca limitata e puntatori | Convalidato, dati mancanti e budget espliciti |
| LIN-011 | R3c | Vista heap glibc 2.36 | 13 + 13 sessioni e quattro casi extra |
| LIN-012 | R3d | Pattern, offset e protezioni ELF | 44 + 44 controlli e 18 prove indipendenti |
| LIN-013 | R3e | Esperimenti persistenti | 14 + 14 controlli, riapertura da revisore separato |
| LIN-013I | R3 | Integrazione e regressioni | Loader unico, due percorsi + replay, R1/R2 ancora validi |
| **LIN-014** | **R4** | **Pacchetto alfa, licenza, matrice e installazione pulita** | **Implementato; Debian e Kali con matrice per modulo, hardware nativo non verificato** |

R3 è completata nel perimetro dichiarato, non coincide con una suite matura o una release distribuita. R4/R5 hanno ora un rapporto separato; nessuna pubblicazione implicita. Daybreak e IA obbligatoria esclusi.

| LIN-015 | R5 | calloc/realloc, quattro regioni e riferimenti codice | Convalidato su glibc 2.36, replay indipendente |
| LIN-016 | R5 | Bridge offline Ghidra con hash/offset/byte | 27 controlli reali, PIE/non-PIE e casi negativi |
| LIN-017 | R5 | Plugin locali fidati per annotazioni | Contratto e sessioni GDB reali; nessuna sandbox dichiarata |
| LIN-018 | R6 | Profilo glibc 2.43 Kali | Implementato: layout/ritorni specifici, corpus e regressione 2.36; gate in R6.md |

Stato corrente e limiti: [rapporto R4/R5](PHASES-4-5.md). Nessuna pubblicazione eseguita; VM rimovibili dopo i test con evidenze conservate.

# R3d — strumenti locali per laboratori

Perimetro: pattern ciclico, ricerca degli offset e proprietà statiche ELF64 little-endian x86-64. Non sono un generatore di exploit e non attribuiscono sfruttabilità. Il modulo usa solo la libreria standard Python; il collaudo Linux usa GCC, GNU readelf e strip già presenti nel laboratorio.

## Uso

Dalla radice del progetto:

```sh
python3 scripts/ressembly-lab.py pattern 128 --width 4 --output work/pattern-new.bin
python3 scripts/ressembly-lab.py offset --integer 0x61616162 --length 128 --width 4 --endian little
python3 scripts/ressembly-lab.py offset --hex 62616161 --length 128 --width 4
python3 scripts/ressembly-lab.py elf work/validation-example/binary
```

Il primo comando crea un file nuovo e rifiuta la sovrascrittura. Senza `--output` scrive i byte senza newline. Un offset è espresso in byte, da zero. La query intera viene convertita nella larghezza ed endian indicati: nessuna troncatura implicita. La query esadecimale è già una sequenza di byte e non viene invertita. Riutilizzare identici lunghezza, larghezza e alfabeto del pattern originale.

La sequenza di de Bruijn non viene ripetuta. Limiti: 1 MiB, larghezze 2–8, alfabeto di 2–64 byte distinti; la CLI accetta un alfabeto ASCII. La ricerca riguarda soltanto il prefisso richiesto e riporta `unique`, `ambiguous` o `not_found`. Una query più corta della larghezza può essere ambigua. Sono conservati al massimo 100 offset, con un flag esplicito se ne esistono altri. Nessun risultato significa che i byte non compaiono nel prefisso cercato, non che un crash non sia controllabile.

## Proprietà ELF e limiti

Il parser non avvia il binario. Accetta ET_EXEC/ET_DYN amd64, massimo 64 MiB, 1024 program header, 8192 sezioni, 100000 simboli complessivi. Numerazione estesa, altre architetture, ELF32 e big-endian sono rifiutati. Le letture hanno controlli di intervallo e budget; il parser non sostituisce un validatore ELF completo o il loader del sistema.

- **PIE:** `yes` richiede ET_DYN e DF_1_PIE; ET_EXEC produce `no`; ET_DYN senza il flag produce `undetermined`, evitando di scambiare una libreria condivisa per un eseguibile PIE.
- **Stack/NX:** il bit eseguibile di PT_GNU_STACK è una proprietà del file; header assente produce `unknown`. `nx_stack=yes` significa richiesta di stack non eseguibile, non una misura dell'effettiva protezione runtime o delle altre mappe.
- **RELRO:** PT_GNU_RELRO e binding immediato (DT_BIND_NOW/DF_BIND_NOW/DF_1_NOW) producono `full_configuration`; solo segmento RELRO produce `partial_configuration`. Sono configurazioni dichiarate, non una verifica dei permessi applicati dal loader.
- **Canary:** si registrano i simboli `__stack_chk_fail`, `__stack_chk_fail_local`, `__stack_chk_guard`, distinti fra definiti e indefiniti. `symbol_present` non dimostra strumentazione di ogni funzione. `not_observed` non dimostra assenza di stack protector. Senza tabelle simboli il risultato è `unknown_no_symbol_tables`.

SHA-256 e dimensione identificano il file letto, senza autenticarne l'origine. Non sono analizzati ASLR runtime, CET, fortify, librerie dipendenti o possibili bypass.

## Convalida ripetibile

```sh
python3 -m unittest discover -s tests -p test_labtools.py -v
python3 scripts/validate-labtools-linux.py work/r3-labtools-new
```

Il secondo comando richiede Linux x86-64 e una directory nuova. Compila il programma C nostro con quattro configurazioni (PIE/canary/full RELRO, non-PIE/partial RELRO, stack eseguibile/no RELRO, libreria condivisa), aggiunge una copia stripped e confronta il parser con gli header, segmenti, dynamic tag e simboli di GNU readelf. Una copia senza section header conserva le proprietà dei segmenti ma dichiara copertura simboli ignota. Input malformato e percorso mancante sono rifiutati. Il dossier conserva comandi, codici di uscita, output raw, proprietà, versioni, risultati e hash dei sorgenti.

Gli 11 test offline verificano vettori noti, unicità delle finestre su cicli piccoli completi, endian, query ambigue, limiti, header incompleti e CLI. Non costituiscono da soli convalida Linux.

Convalida autore eseguita: `work/r3-labtools-001/validation.json`, **44 controlli superati**, inclusa la ripetizione degli 11 test offline. Ambiente: Debian 12 x86-64 emulato QEMU TCG, kernel 6.1.0-54-cloud-amd64, GCC 12.2.0, binutils 2.40, Python 3.11.2. Il dossier è conservato anche sul Mac; i binari sono stati analizzati staticamente, non eseguiti. La mutazione in una copia separata che classificava ogni ET_DYN come PIE è stata intercettata dal test relativo alle librerie condivise (`work/r3-labtools-mutation/result.txt`). Il replay indipendente `work/r3-labtools-independent-001` supera gli stessi 44 controlli; altri 18 controlli indipendenti su pattern e proprietà ELF sono in `work/r3-labtools-review-probes-001`.

## Fonti primarie verificate il 13 novembre 2026

- [GNU ld, opzioni relro, now, execstack, noexecstack](https://sourceware.org/binutils/docs/ld/Options.html).
- [GNU readelf, header, segmenti, dynamic e simboli](https://sourceware.org/binutils/docs/binutils/readelf.html).
- [GCC, opzioni stack protector](https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html).
- [glibc 2.36, strutture e costanti ELF](https://raw.githubusercontent.com/bminor/glibc/release/2.36/master/elf/elf.h).

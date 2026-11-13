# R4 — laboratorio Kali amd64 locale

VM preparata e avviata realmente; provisioning completato. La disponibilità degli strumenti non dichiara ancora compatibilità di tutti i moduli del prodotto.

Il laboratorio è una **VM completa Kali amd64**, distinta dalla VM Debian già usata per R1–R3. Riutilizza soltanto il runtime QEMU 11.1.3 estratto nella cartella di lavoro. L'accelerazione è TCG: esegue un kernel x86-64 e processi reali, ma non misura prestazioni di una CPU x86-64 fisica.

## Provenienza

Immagine ufficiale `kali-linux-2026.3-cloud-genericcloud-amd64.tar.xz`, pubblicata il 24 ottobre 2026 e scaricata dall'URL fissato `https://kali.download/cloud-images/kali-2026.3/`. SHA-256 osservato e corrispondente al file ufficiale `SHA256SUMS`:

```text
087a9c43b6082b0a6aae666debe26c9edf6e3960a90952fc94720e755d628e58
```

La directory cloud pubblica il checksum; la richiesta del file `SHA256SUMS.gpg` ha restituito HTTP404. **Firma separata non verificata**: il controllo effettuato è corrispondenza del checksum distribuito via HTTPS ufficiale, non autenticazione indipendente mediante firma.

L'archivio contiene soltanto `disk.raw`, immagine sparsa con capacità virtuale 25 GiB. Il guest usa un overlay separato; l'immagine originale resta conservata. Spazio host verificato prima del download: circa 38 GiB disponibili. La dimensione compressa è circa 241 MiB.

## Isolamento locale

- File del laboratorio: `work/kali-lab/`, esclusi dalla distribuzione.
- SSH esposto solo su `127.0.0.1:22248`, utente `lab`, chiave dedicata locale, password disabilitata.
- Nessuna modifica a configurazioni SSH, shell o pacchetti globali del Mac.
- Cloud-init installa gli strumenti necessari soltanto dentro il guest: GDB, Python, GCC, binutils e simboli libc.
- Nessun servizio cloud, account, pagamento o pubblicazione.

Avvio/accesso/spegnimento, dalla radice del progetto:

```sh
sh work/kali-lab/start-lab.sh
sh work/kali-lab/ssh-lab.sh 'cat /etc/os-release; uname -m; gdb --version; getconf GNU_LIBC_VERSION'
sh work/kali-lab/stop-lab.sh
```

Non avviare una seconda istanza sullo stesso overlay. Le chiavi, l'immagine e i dati di provisioning rimangono nel laboratorio; non devono entrare nel pacchetto Ressembly.

## Compatibilità da misurare

La matrice deve distinguere installazione, comandi debugger/memoria, strumenti statici e dossier dai moduli vincolati alla versione glibc. Una glibc diversa da quella supportata deve produrre un rifiuto esplicito nei moduli heap interessati, non un PASS inventato né una sostituzione silenziosa dell'allocator. Il successo dell'installazione non basta a certificare tutte le funzionalità.

## Fonti primarie consultate

- [Pagina ufficiale Kali](https://www.kali.org/get-kali/).
- [Indice cloud corrente](https://kali.download/cloud-images/current/), che al momento della verifica elenca Kali2026.3 amd64.
- [Download e verifica delle immagini ufficiali](https://www.kali.org/docs/introduction/download-official-kali-linux-images/).

Log e manifest locali: `work/kali-lab/provision-manifest.json`, `archive-members.json`, `seed-build.log`, `serial.log` e dossier di convalida aggiunti dopo le esecuzioni.

## Versioni effettive registrate

`work/kali-lab/guest-versions.txt` registra: Kali2026.3, kernel `7.1.5+kali-cloud-amd64`, glibc/libc6-dbg `2.43-4`, GDB `17.2-1+b1`, Python GDB `3.14.7`, GCC `16.2.0`, GNU binutils `2.47`. Cloud-init termina con `status: done` e il marker `provision-ready`.

Questa glibc differisce dalla 2.36 originariamente collaudata. Il prossimo dossier distingue i test dell'installazione e dei moduli generali dall'eventuale rifiuto dei profili heap non supportati.

## Primi collaudi installati (pilota, non pacchetto finale)

Il pacchetto `ressembly-r4-pilot003.zip` (SHA-256 `0efc6a048de64433281d7b0e10e8b023b814f9c0b04208190f75cc8380d0c965`) supera 16 controlli installazione/avvio/disinstallazione in un prefisso nuovo con spazi, senza checkout del prodotto nel banco di prova. Dossier `work/kali-lab/package-pilot003`.

La matrice aggiuntiva dei moduli installati supera 10 controlli in `work/kali-lab/installed-pilot003`: contesto e byte confrontati con primitive GDB, plugin locale esplicitamente fidato che produce annotazioni separate, snapshot reale salvato/riaperto, ELF statico, verifica integrità e disinstallazione. **R2, vista strutturale heap e nuova cronologia R5 rifiutano esplicitamente glibc2.43**, senza creare file di cattura ingannevoli. Il successo della matrice significa corretto funzionamento dei moduli generali e corretta diagnostica degli altri, non supporto heap su Kali corrente.

La verifica indipendente dei plugin (sorgenti selezionati, separata dal pacchetto) supera nove test di contratto e due sessioni GDB con 17 controlli: `work/kali-lab/plugins-validation/002`. Primo tentativo conservato per un errore di quoting nel validatore, corretto senza modificare il prodotto. Una mutazione che eliminava il controllo dell'hash fidato è stata intercettata in una copia separata.

Il pacchetto finale richiede un nuovo dossier con il proprio hash.

## Convalida finale e conservazione delle evidenze

I percorsi riservati al collaudo dell'archivio finale sono `work/kali-lab/package-final` e `work/kali-lab/installed-final`. Il relativo `validation.json` registra esito e controlli realmente svolti; il digest dell'archivio è conservato con le evidenze. Questi percorsi non implicano un esito positivo prima dell'esecuzione.

L'utente ha autorizzato la rimozione delle VM al termine delle prove. Prima della rimozione, risultati, versioni, log e manifest vengono copiati sull'host; lo stato della rimozione è registrato separatamente dal coordinatore. I comandi di avvio riportati sopra descrivono il laboratorio impiegato e non promettono un ambiente ancora disponibile dopo la pulizia. Gli archivi pesanti, i dischi e le chiavi del laboratorio sono separati dalle evidenze da conservare.

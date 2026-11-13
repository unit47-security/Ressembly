# Prova pratica dell'alfa locale

Questo percorso usa il pacchetto pilota già verificato nel laboratorio Debian x86-64. Non modifica il Mac e non pubblica nulla. L'installazione di prova è separata dagli esperimenti di sviluppo. Il collaudo automatico non equivale alla tua esperienza nell'usarla: annota dove le istruzioni risultano poco chiare.

Con la VM Debian accesa, apri un Terminale del Mac:

```sh
cd /Users/user/Documents/ChatGPT/Ressembly
sh work/linux-lab/ssh-lab.sh -t '/home/lab/ressembly-user-trial/bin/ressembly gdb /home/lab/ressembly-user-work/debug_lab'
```

Al prompt GDB inserisci, uno alla volta:

```gdb
set pagination off
break debug_stop
run
rs-context
rs-maps
rs-help
quit
```

Per uscire conferma la chiusura del programma didattico se GDB lo chiede. Cosa verificare: riesci ad avviare il debugger dalla guida, leggere assembly/registri/stack e ritrovare i comandi senza assistenza? Non servono diagnosi di vulnerabilità. Comunica l'esito e gli eventuali passaggi poco chiari.

Il pilota non è ancora l'archivio conclusivo R4/R5. Le prove tecniche finali verranno ripetute sul pacchetto definitivo; questa è la prova umana del percorso d'uso. Se viene rinviata, il rapporto la indicherà come non eseguita, senza sostituirla con un agente.

## Esito registrato

L'utente ha riferito «tutto ok ottimo» dopo la prova di contesto, mappe e aiuto. Il primo incollaggio di più righe ha causato difficoltà; risolto inserendo **un comando per volta**. Registrazione: `work/r4-r5-gates/user-trial.json`. Questa è una conferma dell'utilizzatore, non una misura indipendente di velocità o correttezza di ogni modulo. Dopo la rimozione autorizzata delle VM, il comando SSH sopra resta documentazione storica: occorre ricreare un laboratorio per ripeterlo.

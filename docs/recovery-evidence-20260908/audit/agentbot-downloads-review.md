# AgentBot: 104 download falliti — review locale 8 settembre 2026

## Esito

Non è dimostrata la causa dei 104 fallimenti della scansione terminata alle 01:55 CEST. È corretta una lacuna diagnostica concreta: il log applicativo ora elenca tutti i simboli ancora privi di dati utilizzabili dopo il retry. La modifica non risolve né pretende di risolvere i download originali.

Repository `/root/AgentBot`, HEAD `0220574d4712e7dc4f7aa95bd178e32c10ac951c`. Nessun AGENTS.md locale trovato. Rispettate istruzioni globali e incarico ricevuto; nessuna delega ulteriore.

## Evidenza e percorso completo

- `/root/reports/system-efficiency-20260908/agentbot-post-restart.log` contiene quattro righe aggregate. La riga delle 01:55:02,901 riporta 388 stock, 0 segnali, 0 errori e 104 download falliti. Mancano elenco dei ticker, errori yfinance e dettaglio della prima passata. `alerts.log` nel repository risale a marzo e non documenta questa scansione.
- `bot.py:466` (`scan_all`) invoca `download_batch` dalla prima passata e dalla passata di retry; sono i soli chiamanti del downloader live. Un'eccezione di batch inserisce l'intero batch fra i falliti; una risposta senza il ticker o con frame vuoto inserisce quel ticker. Il secondo tentativo usa batch da 20. Il totale persistito è `len(still_failing)` dopo il retry, non il numero di chiamate fallite.
- `bot.py:195` (`download_batch`) chiama yfinance per candele 1h di 30 giorni; `_normalize_ohlc` (`bot.py:162`) gestisce MultiIndex, duplicati e colonne OHLC mancanti. Risposta vuota, colonne mancanti, ticker assente e righe interamente NaN confluiscono nello stesso esito senza dati. Non si può distinguere indisponibilità del provider, simbolo non disponibile o risposta inutilizzabile dal contatore salvato.
- `errors_count` misura gli errori restituiti da `process_ticker`, quindi "0 errori" non contraddice i 104 download falliti. 104/388 = 26,8%; il ramo di pulizia cache post-scan richiede oltre il 50% (`bot.py:618`) e con questi contatori non scatta. `cleanup_stale_locks` viene anche chiamata all'avvio (`bot.py:767`); il log disponibile non prova né esclude un problema SQLite.
- `yf_cache.py:29` controlla i database locali prima della rimozione dei sidecar. Non è stata invocata né sono stati aperti database/cache reali durante questa review. Nessun intervento sulla cache è giustificato dai dati disponibili.
- `_update_fail_streaks` (`bot.py:117`) esclude i ticker dopo cinque scansioni fallite consecutive, conservando lo stato solo in RAM; il riavvio azzera quello stato. Il log preesistente mostra i primi 20 esclusi soltanto al raggiungimento della soglia: non identifica i 104 fallimenti della prima scansione dopo il riavvio.
- La scansione iniziata il 7 settembre UTC ricade ancora nel 7 settembre a New York. Il calendario locale codifica il primo lunedì di settembre come festività USA e filtra i simboli senza suffisso di borsa; `stocks.py` conserva elenchi statici IT/EU. Questo è coerente con una scansione limitata a titoli europei; non dimostra quali dei loro simboli fossero disponibili al provider.
- Nel pacchetto yfinance locale 1.2.0, `multi.py:173` emette gli errori del provider tramite il logger `yfinance`, mentre gli handler del bot sono associati a `BotAlarm`. Non sono presenti gli errori di tale logger nell'estratto acquisito. La versione del container non è stata verificata.
- `backtest.py:43` ha un downloader autonomo, chiamato soltanto dal backtest; non partecipa alla scansione live oggetto dell'incarico.

## Diff

- `bot.py:582`: cinque righe aggiungono un warning dopo il riepilogo retry, solo quando rimangono fallimenti. Contiene il numero e l'elenco completo dei simboli; esclude i recuperati. La dicitura "senza dati utilizzabili" non attribuisce arbitrariamente la causa al provider.
- `tests/test_download_diagnostics.py`: una regressione offline esegue `scan_all` con download e servizi simulati. Copre 25 fallimenti finali (oltre il limite diagnostico preesistente di 20), un recupero, contatori e numero di ticker processati; seconda variante con recupero di tutti e nessun warning.
- Preservati `.dockerignore` già modificato e `.codex` preesistente. Nessuna modifica a configurazione, universo titoli, trading, dati, cache o dipendenze; nessun accesso a `.env`, credenziali, provider o runtime Docker; nessun restart, commit o push.

## Verifica

`git diff --check` passa. Il primo launcher ha passato il gate risorse ma si è fermato prima dei test perché `argv[0]` non era il percorso assoluto del Python standalone (`encodings` non trovato); corretto soltanto il comando. Il secondo ha rivelato che il venv locale non contiene psycopg2, sempre prima dell'esecuzione del test. Entrambi gli errori sono conservati in `agentbot-download-check-launcher-failed.log` e `agentbot-download-check.log`, nella directory di questo report.

La verifica finale usa il driver DB simulato soltanto nel launcher offline, con accessi `connect` e `execute_values` che generano AssertionError. Non sono state installate dipendenze; il test esercita `scan_all` reale. È passata (exit 0, entrambe le varianti) sotto `flock /tmp/codex-recovery-20260908/heavy.lock`, con MemAvailable 5.574.288 KiB (5,32 GiB), memory PSI some avg10 0,14, un processo e variabili OMP/OpenBLAS a 1. Gate interno rispettato: MemAvailable >= 4 GiB e PSI <= 5. Risultato finale nel log `agentbot-download-check.log`. Non sono state ripetute prove verdi; i primi due avvii erano falliti prima del test. Comando riproducibile:

```sh
flock /tmp/codex-recovery-20260908/heavy.lock env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /root/AgentBot/.venv/bin/python /tmp/system-efficiency-20260908/agentbot-download-check-runner.py
```

## Residuo operativo

I 104 fallimenti originali restano non attribuibili con gli artefatti disponibili. La patch è soltanto locale e non è stata attivata. Dopo una futura attivazione autorizzata, conservare il warning completo e gli errori yfinance della stessa scansione permetterà di distinguere simboli non disponibili, risposte vuote, rate limit e problemi SQLite; nessun titolo va eliminato sulla base del solo contatore.

# AgentBot — review aggiuntiva in sola lettura

Conclusa l'8 settembre 2026 alle 02:59 CEST. Due difetti riprodotti nella gestione degli errori; nessuna evidenza critica. Nessuna modifica al repository.

## Revisione verificata

HEAD letto direttamente da `.git/HEAD` e `.git/refs/heads/main`, senza comandi Git: `0220574d4712e7dc4f7aa95bd178e32c10ac951c`. L'albero può contenere modifiche successive al commit: fanno fede gli hash dei file effettivamente letti, ricontrollati alle 02:58:47 CEST.

- `bot.py`: `d61fe114c415960a2b4322acbfe7a317591e08a792508026a98961f8d7058d6b`
- `db.py`: `306f8971f518c181b7cf92db809ea269f29b3ac3ef7d4bc359734fa2317f743c`
- `tests/test_download_diagnostics.py`: `15bb04ab34be5f5df42fd039eb1134b02cad6dd82bcd1dcfa27f320d5ecc16eb`

Letti i rapporti precedenti pertinenti: `/tmp/codex-recovery-20260908/audit-host-finale.md` e `/root/reports/system-efficiency-20260908/RAPPORTO.md`. I 104 download falliti e i limiti di swap erano già segnalati; non vengono ripresentati come nuove scoperte. Nessun `AGENTS.md` presente nei percorsi `/`, `/root`, `/root/AgentBot`, né tra i file censiti nel repository.

## P2 — Gli errori di persistenza delle candele non entrano nel contatore

**Posizione:** `/root/AgentBot/bot.py:307`.

L'eccezione di `save_candles` viene registrata ma non incrementa `errors`. La catena `process_ticker → scan_all._process_one → complete_scan` trasmette quindi zero al campo `scans.errors` e al riepilogo, anche se il salvataggio delle candele è fallito. Gli errori S/R e segnali, invece, incrementano già lo stesso contatore.

**Prova locale:** 16 candele sintetiche OHLCV valide, nessun breakout; `save_candles` sostituita con una funzione che solleva `RuntimeError`. Falliscono entrambe le scritture 1h/4h: il logger riceve due errori, `process_ticker` restituisce `(0, 0, 0)`. Il comportamento persiste nella rilettura finale.

**Rimedio minimo:** aggiungere `errors += 1` nel relativo `except`, mantenendo l'isolamento della scansione. La prova non dimostra che questo errore si sia verificato nelle scansioni reali precedenti.

## P2 — Un frame OHLC accettato senza Volume perde il segnale senza diagnosi

**Posizione:** `/root/AgentBot/bot.py:149`, `/root/AgentBot/bot.py:273`.

`_normalize_ohlc` accetta esplicitamente un frame contenente Open/High/Low/Close; `download_batch` lo restituisce come download riuscito. Anche il salvataggio gestisce Volume assente. `resample_to_4h`, però, richiede sempre Volume: l'aggregazione solleva `KeyError`, catturato senza log né incremento degli errori; il frame 4h diventa vuoto e la conferma del segnale viene saltata. Entrambi i percorsi download, prima passata e retry, arrivano allo stesso `process_ticker`.

**Prova locale:** con OHLC identici e breakout finale, il frame completo restituisce `(1, 0, 0)`; tolta esclusivamente Volume, il normalizzatore continua ad accettarlo ma il risultato diventa `(0, 0, 0)`, senza errori registrati.

**Rimedio minimo:** includere l'aggregazione Volume soltanto quando la colonna esiste, coerentemente con il contratto OHLC già presente. Registrare e contare eventuali altri errori di resampling. È dimostrato il difetto con un input accettato dal codice; non è stato verificato che il provider abbia realmente restituito tale schema nei 104 fallimenti precedenti.

## Riproduzione e limiti

Microprova salvata fuori dal repository: `agentbot-repro.py` nella stessa directory. Comando:

```sh
/root/AgentBot/.venv/bin/python -B /tmp/codex-recovery-20260908/accelerazione/host/agentbot-repro.py
```

Esito: tutte le asserzioni passate. La prova compila soltanto quattro definizioni AST del sorgente e usa pandas già installato, dati sintetici e funzioni simulate; non importa il modulo bot e non apre DB, log applicativi o rete.

Il test diagnostico esistente verifica l'elenco completo dei fallimenti finali e l'esclusione dei recuperati, ma simula `process_ticker`: non copre questi due difetti. Non eseguite suite, build, installazioni, comandi Git o interventi su servizi/configurazioni. Nessun difetto nuovo di crescita dei buffer dimostrato; manca una misura runtime autorizzata per attribuire il consumo di memoria. Nessuna patch applicata o preparata.

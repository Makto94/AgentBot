# Handoff di ripresa — Makto94/AgentBot — 8 settembre 2026

Recuperare diagnostica download, review della persistenza/Volume e limiti RAM/swap.

Documento canonico sul ramo `main`. Distingue codice salvato, proposte e verifiche mancanti; non certifica un rilascio applicativo. I documenti storici sono conservati e gli eventuali loro stati precedenti vanno letti insieme agli aggiornamenti qui sotto.

## Aggiornamento autorizzato dopo il recupero

L’operatore ha autorizzato completamento dei residui piccoli, merge e deploy dopo i controlli. Corretti conteggio errori save_candles, aggregazione OHLC senza Volume e diagnosi degli altri errori di resampling. Prove offline passate, inclusi due salvataggi falliti, stesso segnale con/senza Volume, errore aggregazione e diagnostica retry. Configurazione e container corrente coincidono: 1536 MiB RAM e memoria+swap uguale alla RAM, quindi swap disabilitato. Build/rilascio in preparazione; la causa dei download storici non viene inventata.

## Autorizzazioni e perimetro

La richiesta corrente autorizza la pubblicazione di questo handoff e dei branch di recupero, con push normale e senza rilasci automatici. Non autorizza a completare adesso le correzioni applicative, fondere codice incompleto nel ramo principale, avviare sessioni ferme, cancellare/archiviare chat, modificare dati storici, acquistare servizi o intervenire in produzione. Gli interventi operativi menzionati sotto appartengono alle sessioni originarie, non sono stati ripetuti.

Le sei unità di recupero originarie risultavano non in esecuzione al controllo di questa consegna. Le sessioni e le sorgenti locali sono conservate. Database, segreti, dati personali e artefatti voluminosi non fanno parte degli allegati selezionati.

## Revisioni da cui riprendere

Base del commit documentale: [`0220574d4712e7dc4f7aa95bd178e32c10ac951c`](https://github.com/Makto94/AgentBot/commit/0220574d4712e7dc4f7aa95bd178e32c10ac951c), riletta dal remoto. Il ramo principale riceve soltanto questo documento. Ogni snapshot conserva il proprio genitore e il diff pertinente, senza fondere worktree divergenti.

| Filone | Branch di recupero | Commit snapshot | Base originale |
|---|---|---|---|
| audit | [`recovery/2026-09-08/audit`](https://github.com/Makto94/AgentBot/tree/recovery/2026-09-08/audit) | [`51ab5b132b3a`](https://github.com/Makto94/AgentBot/commit/51ab5b132b3a989f79bea86467a4ee3bfae2a77c) | `0220574d4712e7dc4f7aa95bd178e32c10ac951c` |

Gli snapshot sono punti di ripresa, non branch da integrare integralmente. Il manifest elenca file copiati, impronte SHA-256, esclusioni e origine storica; i file non modificati restano nella storia Git. I percorsi server nei documenti storici indicano la provenienza: non servono per leggere codice e prove su GitHub.

- [Manifest audit](https://github.com/Makto94/AgentBot/blob/51ab5b132b3a989f79bea86467a4ee3bfae2a77c/docs/recovery-evidence-20260908/snapshot.json)

## Lavoro salvato

- bot.py registra i download rimasti falliti dopo i retry; recuperati esclusi dal warning e contatori preesistenti conservati. Modifiche applicative locali, non immagine runtime aggiornata.
- Il worktree review-download è byte-identico allo snapshot audit. Il marker .codex vuoto preesistente resta sul server e non è confuso con codice dell’audit.
- Nella sessione operativa il limite swap è stato riallineato senza restart; non è dimostrata una soluzione permanente alla mancata applicazione dello zero agli avvii.

## Incompleto e proposte da verificare

- La causa dei 104 download storici falliti non è dimostrata dalla nuova diagnostica.
- Due difetti della review restano proposte: save_candles fallito non incrementa errors; un frame OHLC senza Volume può perdere il segnale senza diagnosi.
- Il codice del warning non era attivo nell’immagine di servizio letta; non dichiarare già distribuita la correzione.

## Prove recuperate e loro limiti

- Prova offline: 25 fallimenti residui segnalati, recuperati esclusi e nessun warning quando recuperano tutti.
- Microprove sintetiche dei due difetti allegate; non sono test del provider o della strategia su mercati reali.

I risultati sopra sono storici e valgono per le revisioni o impronte indicate nei relativi rapporti/log. Dove manca un legame certo con l’ultimo diff, la verifica finale rimane aperta. Per il recupero sono stati confrontati gli snapshot con le sorgenti, controllati i file selezionati e i blob dei commit inediti per segreti/artefatti; le occorrenze delle scansioni nei test sono fixture, non credenziali operative. Non sono state ripetute suite applicative per il solo salvataggio documentale.

## File e prove leggibili da GitHub

- [Diagnostica download](https://github.com/Makto94/AgentBot/blob/51ab5b132b3a989f79bea86467a4ee3bfae2a77c/docs/recovery-evidence-20260908/audit/agentbot-downloads-review.md)
- [Prova offline](https://github.com/Makto94/AgentBot/blob/51ab5b132b3a989f79bea86467a4ee3bfae2a77c/docs/recovery-evidence-20260908/audit/agentbot-download-check.log)
- [Persistenza e Volume](https://github.com/Makto94/AgentBot/blob/51ab5b132b3a989f79bea86467a4ee3bfae2a77c/docs/recovery-evidence-20260908/controverifica/AGENTBOT.md)

## Passi per terminare

1. Riprendere audit, leggere bot.py, db.py, test diagnostico e AGENTBOT.md allegato.
2. Contare i fallimenti di persistenza nello stesso percorso che alimenta scans.errors; validare/reportare Volume mancante senza inventare valori.
3. Aggiungere i casi di errore alle prove offline esistenti e verificare riepilogo finale e isolamento degli errori.
4. Diagnosticare separatamente la persistenza del limite swap e i download reali solo con accesso autorizzato; non cambiare Docker condiviso o strategia senza un incarico specifico.

## Dipendenze e accesso al server

Provider, database e impostazioni RAM/swap richiedono il server; nessuna credenziale o dato di mercato è incluso. Deploy dell’immagine e interventi runtime non sono autorizzati dalla pubblicazione documentale.

## Sessioni coinvolte

Identificativi di provenienza, non istruzioni per riavviare le chat. I transcript completi restano conservati e non vengono pubblicati. Le conclusioni utili sono riportate in questo documento e negli allegati.

- audit-host: `01a07e21-8bf0-7d53-8f60-51a2a3e9bf73`.

Sottoagenti pertinenti recuperati:

- /root/agentbot_downloads: `01a07e76-4937-7642-aceb-4dd889e05aa2`.
- /root/agentbot_correctness: `01a07e9b-1ad1-7fb1-88ea-7f9c7a85420f`.

Controrevisioni aggiuntive:

- host: `01a07e83-ac4f-7d03-a771-f21498a9bc1c`.

## Ripresa con accesso GitHub soltanto

Leggere questo handoff, aprire il commit snapshot scelto e confrontarlo con il ramo principale aggiornato. Se l’ambiente consente solo lettura, produrre patch unificate applicabili e comandi di verifica, separando ciò che è stato realmente eseguito da ciò che richiede il server. Non dichiarare modifiche, test, merge o deploy mai eseguiti.

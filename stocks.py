"""
Modulo per il recupero dinamico di tutti i ticker USA e Italia.
- USA: S&P 500 + NASDAQ-100 (scraping da Wikipedia)
- Italia: FTSE MIB + FTSE Italia Mid Cap + Small Cap (lista completa Borsa Italiana, suffisso .MI)
"""

import logging
from io import StringIO

import pandas as pd
import requests

logger = logging.getLogger("BotAlarm")

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})


def _fetch_html(url: str) -> str:
    """Scarica HTML con User-Agent valido per evitare 403."""
    resp = _SESSION.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def get_sp500() -> list[str]:
    """Scarica la lista S&P 500 da Wikipedia."""
    try:
        html = _fetch_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
        tables = pd.read_html(StringIO(html))
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        logger.info(f"S&P 500: {len(tickers)} ticker caricati")
        return tickers
    except Exception as e:
        logger.error(f"Errore fetch S&P 500: {e}")
        return []


def get_nasdaq100() -> list[str]:
    """Scarica la lista NASDAQ-100 da Wikipedia."""
    try:
        html = _fetch_html("https://en.wikipedia.org/wiki/Nasdaq-100")
        tables = pd.read_html(StringIO(html))
        for table in tables:
            if "Ticker" in table.columns:
                tickers = table["Ticker"].str.replace(".", "-", regex=False).tolist()
                logger.info(f"NASDAQ-100: {len(tickers)} ticker caricati")
                return tickers
            if "Symbol" in table.columns:
                tickers = table["Symbol"].str.replace(".", "-", regex=False).tolist()
                logger.info(f"NASDAQ-100: {len(tickers)} ticker caricati")
                return tickers
        logger.warning("NASDAQ-100: tabella non trovata, uso fallback")
        return []
    except Exception as e:
        logger.error(f"Errore fetch NASDAQ-100: {e}")
        return []


# ── Borsa Italiana ──────────────────────────────────────────────────────
# FTSE MIB (40 blue chip) + FTSE Italia Mid Cap + Small Cap
# Suffisso .MI per Yahoo Finance

ITALY_STOCKS = [
    # ── FTSE MIB ──
    "A2A.MI", "AMP.MI", "AZM.MI", "BGN.MI", "BMED.MI",
    "BPE.MI", "BZU.MI", "CPR.MI", "DIA.MI", "ENEL.MI",
    "ENI.MI", "ERG.MI", "FBK.MI", "G.MI", "HER.MI",
    "IG.MI", "INW.MI", "IP.MI", "ISP.MI", "ITW.MI",
    "LDO.MI", "MB.MI", "MONC.MI", "NEXI.MI", "PIRC.MI",
    "PRY.MI", "PST.MI", "REC.MI", "SRG.MI", "STM.MI",
    "STMMI.MI", "TEN.MI", "TIT.MI", "TRN.MI", "UCG.MI",
    "UNI.MI", "US.MI",
    # ── FTSE Italia Mid Cap ──
    "ADB.MI", "ALK.MI", "ANT.MI", "ARN.MI", "ASC.MI",
    "ATS.MI", "BC.MI", "BAMI.MI", "BFE.MI", "BSS.MI",
    "CASS.MI", "CE.MI", "CEM.MI", "CIR.MI", "CLT.MI",
    "CNHI.MI", "CRL.MI", "CTO.MI", "DANR.MI", "DEA.MI",
    "DLG.MI", "DMN.MI", "ECK.MI", "ELN.MI", "ENAV.MI",
    "EQUI.MI", "FNM.MI", "GEO.MI", "GPI.MI", "GVS.MI",
    "IDB.MI", "IFI.MI", "IGD.MI", "IMA.MI", "IVG.MI",
    "LR.MI", "MARR.MI", "MASI.MI", "MIT.MI", "MUTU.MI",
    "NPI.MI", "ORS.MI", "OVS.MI", "PIA.MI", "PINF.MI",
    "PLT.MI", "PQA.MI", "PRL.MI", "RACE.MI", "RCS.MI",
    "REY.MI", "SAB.MI", "SALC.MI", "SES.MI", "SFL.MI",
    "SOL.MI", "SPM.MI", "SRS.MI", "TFI.MI", "TIP.MI",
    "TOD.MI", "TPRO.MI", "UNIR.MI", "VIV.MI", "WBD.MI",
    "WIIT.MI", "ZV.MI",
    # ── Small Cap / Star ──
    "ACE.MI", "AERI.MI", "AIR.MI", "ALA.MI", "ALFIO.MI",
    "ATON.MI", "BAN.MI", "CAD.MI", "CALT.MI", "CAT.MI",
    "CDR.MI", "CFP.MI", "CLE.MI", "CLIQ.MI", "COPT.MI",
    "COR.MI", "COS.MI", "CY4.MI", "DAL.MI", "DAN.MI",
    "DATA.MI", "DHH.MI", "DIB.MI", "DIGI.MI", "DIS.MI",
    "DM.MI", "DOX.MI", "EAG.MI", "EBT.MI", "ELES.MI",
    "EMAK.MI", "ENER.MI", "EPA.MI", "EUK.MI", "EVE.MI",
    "EXA.MI", "FAT.MI", "FCM.MI", "FILA.MI", "FM.MI",
    "FON.MI", "FOPE.MI", "GCN.MI", "GHN.MI", "GRE.MI",
    "GRP.MI", "ICF.MI", "ILP.MI", "INC.MI", "INGA.MI",
    "INTEK.MI", "IRC.MI", "ITD.MI", "ITM.MI", "JUV.MI",
    "KME.MI", "KRE.MI", "LAZ.MI", "LDB.MI", "LUVE.MI",
    "MARP.MI", "MAT.MI", "MCM.MI", "MDC.MI", "MOL.MI",
    "MON.MI", "MOR.MI", "MPT.MI", "MTA.MI", "NES.MI",
    "NET.MI", "NTH.MI", "OLI.MI", "OPTI.MI", "PAN.MI",
    "PAT.MI", "PH.MI", "PNT.MI", "POR.MI", "PRT.MI",
    "RBC.MI", "REA.MI", "RFT.MI", "RIV.MI", "RN.MI",
    "ROM.MI", "ROSE.MI", "RST.MI", "RWAY.MI", "SCF.MI",
    "SCI.MI", "SGR.MI", "SIF.MI", "SITI.MI", "SKA.MI",
    "SOS.MI", "SSB.MI", "STAR.MI", "SVS.MI", "TAS.MI",
    "TES.MI", "TIS.MI", "TKA.MI", "TXT.MI", "UCM.MI",
    "VIM.MI", "VIS.MI", "VLS.MI", "VNE.MI", "WRMN.MI",
]


def get_all_us_stocks() -> list[str]:
    """Restituisce tutti i ticker USA (S&P 500 + NASDAQ-100, senza duplicati)."""
    sp500 = get_sp500()
    nasdaq = get_nasdaq100()
    combined = list(dict.fromkeys(sp500 + nasdaq))
    logger.info(f"Totale USA (senza duplicati): {len(combined)} ticker")
    return combined


def get_all_italy_stocks() -> list[str]:
    """Restituisce tutti i ticker italiani (.MI)."""
    logger.info(f"Totale Italia: {len(ITALY_STOCKS)} ticker")
    return ITALY_STOCKS


def get_all_stocks() -> list[str]:
    """Restituisce tutti i ticker USA + Italia."""
    us = get_all_us_stocks()
    ita = get_all_italy_stocks()
    all_stocks = us + ita
    logger.info(f"Totale complessivo: {len(all_stocks)} ticker ({len(us)} USA + {len(ita)} ITA)")
    return all_stocks

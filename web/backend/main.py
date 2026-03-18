"""FastAPI application for Stock Scanner Dashboard."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from database import (
    close_db,
    get_all_tickers,
    get_latest_signals,
    get_scanner_stats,
    get_scanner_status,
    get_scans,
    get_signals_paginated,
    get_ticker_chart,
    get_ticker_signals,
    get_tickers_list,
    init_db,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Stock Scanner API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/scanner/status")
async def scanner_status():
    return await get_scanner_status()


@app.get("/api/scanner/stats")
async def scanner_stats():
    return await get_scanner_stats()


@app.get("/api/signals")
async def signals_list(
    page: int = 1,
    page_size: int = 25,
    ticker: str | None = None,
    type: str | None = None,
    timeframe: str | None = None,
    near_sr: bool | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    if page < 1:
        page = 1
    if page_size not in (25, 50, 100):
        page_size = 25
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    for label, val in [("date_from", date_from), ("date_to", date_to)]:
        if val is not None:
            try:
                datetime.strptime(val, "%Y-%m-%d")
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid {label} format. Use YYYY-MM-DD") from exc

    return await get_signals_paginated(
        page=page,
        page_size=page_size,
        ticker=ticker,
        signal_type=type,
        timeframe=timeframe,
        near_sr=near_sr,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@app.get("/api/signals/latest")
async def signals_latest(limit: int = 20):
    if limit < 1 or limit > 100:
        limit = 20
    return {"signals": await get_latest_signals(limit)}


@app.get("/api/ticker/{ticker}/chart")
async def ticker_chart(ticker: str):
    return await get_ticker_chart(ticker)


@app.get("/api/ticker/{ticker}/signals")
async def ticker_signals(ticker: str):
    return {"signals": await get_ticker_signals(ticker)}


@app.get("/api/tickers")
async def tickers_list():
    return {"tickers": await get_tickers_list()}


@app.get("/api/tickers/all")
async def tickers_all(q: str = ""):
    """Get all monitored tickers, optionally filtered by search query."""
    return {"tickers": await get_all_tickers(q)}


@app.get("/api/scans")
async def scans_list(limit: int = 20):
    if limit < 1 or limit > 100:
        limit = 20
    return {"scans": await get_scans(limit)}


@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

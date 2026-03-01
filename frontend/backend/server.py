"""FastAPI server for US Stocks AI recommendations."""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import database as db
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import json
import time

# Add parent directories to path for importing trading agents
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import shared logging system
from tradingagents.log_utils import add_log, analysis_logs, log_lock, log_subscribers

# Track running analyses
# NOTE: This is not thread-safe for production multi-worker deployments.
# For production, use Redis or a database-backed job queue instead.
running_analyses = {}  # {symbol: {task_id, date, status, started_at, completed_at, progress, ...}}

# Track symbol by task_id for task-scoped polling/queries
task_to_symbol = {}

app = FastAPI(
    title="US Stocks AI API",
    description="API for S&P 500 Top 50 stock recommendations",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StockAnalysis(BaseModel):
    symbol: str
    company_name: str
    decision: Optional[str] = None
    confidence: Optional[str] = None
    risk: Optional[str] = None
    raw_analysis: Optional[str] = None


class TopPick(BaseModel):
    rank: int
    symbol: str
    company_name: str
    decision: str
    reason: str
    risk_level: str


class StockToAvoid(BaseModel):
    symbol: str
    company_name: str
    reason: str


class Summary(BaseModel):
    total: int
    buy: int
    sell: int
    hold: int


class DailyRecommendation(BaseModel):
    date: str
    analysis: dict[str, StockAnalysis]
    summary: Summary
    top_picks: list[TopPick]
    stocks_to_avoid: list[StockToAvoid]


class SaveRecommendationRequest(BaseModel):
    date: str
    analysis: dict
    summary: dict
    top_picks: list
    stocks_to_avoid: list


# ============== Pipeline Data Models ==============

class AgentReport(BaseModel):
    agent_type: str
    report_content: str
    data_sources_used: Optional[list] = []
    created_at: Optional[str] = None


class DebateHistory(BaseModel):
    debate_type: str
    bull_arguments: Optional[str] = None
    bear_arguments: Optional[str] = None
    risky_arguments: Optional[str] = None
    safe_arguments: Optional[str] = None
    neutral_arguments: Optional[str] = None
    judge_decision: Optional[str] = None
    full_history: Optional[str] = None


class PipelineStep(BaseModel):
    step_number: int
    step_name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    output_summary: Optional[str] = None


class DataSourceLog(BaseModel):
    source_type: str
    source_name: str
    data_fetched: Optional[dict] = None
    fetch_timestamp: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


class SavePipelineDataRequest(BaseModel):
    date: str
    symbol: str
    agent_reports: Optional[dict] = None
    investment_debate: Optional[dict] = None
    risk_debate: Optional[dict] = None
    pipeline_steps: Optional[list] = None
    data_sources: Optional[list] = None


class AnalysisConfig(BaseModel):
    deep_think_model: Optional[str] = "opus"
    quick_think_model: Optional[str] = "sonnet"
    provider: Optional[str] = "claude_subscription"  # claude_subscription or anthropic_api
    api_key: Optional[str] = None
    max_debate_rounds: Optional[int] = 1


class RunAnalysisRequest(BaseModel):
    symbol: str
    date: Optional[str] = None  # Defaults to today if not provided
    config: Optional[AnalysisConfig] = None


def _is_cancelled(symbol: str) -> bool:
    """Check if an analysis has been cancelled."""
    return running_analyses.get(symbol, {}).get("cancelled", False)


def _get_status_by_task_id(task_id: str) -> Optional[dict]:
    symbol = task_to_symbol.get(task_id)
    if not symbol:
        for sym, data in running_analyses.items():
            if data.get("task_id") == task_id:
                task_to_symbol[task_id] = sym
                symbol = sym
                break

    if symbol and symbol in running_analyses:
        return {"symbol": symbol, **running_analyses[symbol]}

    task = db.get_task(task_id)
    if not task:
        return None

    return {
        "task_id": task_id,
        "symbol": task.get("request_symbol"),
        "date": task.get("analysis_date"),
        "status": task.get("status"),
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "progress": "",
    }


def run_analysis_task(task_id: str, symbol: str, date: str, analysis_config: dict = None):
    """Background task to run trading analysis for a stock."""
    global running_analyses

    print(f"[TaskLifecycle] run_analysis_task entered | task_id={task_id} symbol={symbol} date={date}", flush=True)

    # Default config values
    if analysis_config is None:
        analysis_config = {}

    deep_think_model = analysis_config.get("deep_think_model", "opus")
    quick_think_model = analysis_config.get("quick_think_model", "sonnet")
    provider = analysis_config.get("provider", "claude_subscription")
    api_key = analysis_config.get("api_key")
    max_debate_rounds = analysis_config.get("max_debate_rounds", 1)

    try:
        task_to_symbol[task_id] = symbol
        running_analyses[symbol] = {
            "task_id": task_id,
            "date": date,
            "status": "initializing",
            "started_at": datetime.now().isoformat(),
            "progress": "Loading trading agents...",
            "cancelled": False,
        }

        db.update_analysis_task_status(
            task_id,
            status="running",
            started_at=running_analyses[symbol]["started_at"],
            total=1,
            completed=0,
            failed=0,
            skipped=0,
        )

        add_log("info", "system", f"🚀 Starting analysis for {symbol} on {date}")
        add_log("info", "system", f"Config: deep_think={deep_think_model}, quick_think={quick_think_model}")

        # Import trading agents
        add_log("info", "system", "Loading TradingAgentsGraph module...")
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        running_analyses[symbol]["progress"] = "Initializing analysis pipeline..."
        add_log("info", "system", "Initializing analysis pipeline...")

        # Create config from user settings
        config = DEFAULT_CONFIG.copy()
        config["llm_provider"] = "anthropic"  # Use Claude for all LLM
        config["deep_think_llm"] = deep_think_model
        config["quick_think_llm"] = quick_think_model
        config["max_debate_rounds"] = max_debate_rounds

        # If using API provider and key is provided, set it in environment
        if provider == "anthropic_api" and api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key

        # Check cancellation before starting
        if _is_cancelled(symbol):
            add_log("info", "system", f"Analysis for {symbol} was cancelled before starting")
            running_analyses[symbol]["status"] = "cancelled"
            running_analyses[symbol]["progress"] = "Analysis cancelled"
            running_analyses[symbol]["completed_at"] = datetime.now().isoformat()
            db.update_analysis_task_status(
                task_id,
                status="cancelled",
                completed=0,
                failed=1,
                completed_at=running_analyses[symbol]["completed_at"],
            )
            return

        running_analyses[symbol]["status"] = "running"
        running_analyses[symbol]["progress"] = f"Running market analysis (model: {deep_think_model})..."

        add_log("agent", "system", f"Creating TradingAgentsGraph for {symbol}...")

        # Initialize and run
        ta = TradingAgentsGraph(debug=False, config=config)

        # Check cancellation before graph execution
        if _is_cancelled(symbol):
            add_log("info", "system", f"Analysis for {symbol} was cancelled before graph execution")
            running_analyses[symbol]["status"] = "cancelled"
            running_analyses[symbol]["progress"] = "Analysis cancelled"
            running_analyses[symbol]["completed_at"] = datetime.now().isoformat()
            db.update_analysis_task_status(
                task_id,
                status="cancelled",
                completed=0,
                failed=1,
                completed_at=running_analyses[symbol]["completed_at"],
            )
            return

        running_analyses[symbol]["progress"] = f"Analyzing {symbol}..."
        add_log("agent", "system", f"Starting propagation for {symbol}...")
        add_log("data", "data_fetch", f"Fetching market data for {symbol}...")

        final_state, decision, hold_days, confidence, risk = ta.propagate(symbol, date)

        # Check cancellation after graph execution (skip saving results)
        if _is_cancelled(symbol):
            add_log("info", "system", f"Analysis for {symbol} was cancelled after completion — results discarded")
            running_analyses[symbol]["status"] = "cancelled"
            running_analyses[symbol]["progress"] = "Analysis cancelled (results discarded)"
            running_analyses[symbol]["completed_at"] = datetime.now().isoformat()
            db.update_analysis_task_status(
                task_id,
                status="cancelled",
                completed=0,
                failed=1,
                completed_at=running_analyses[symbol]["completed_at"],
            )
            return

        add_log("success", "system", f"✅ Analysis complete for {symbol}: {decision}")

        # Extract raw analysis from final_state if available
        raw_analysis = ""
        if final_state:
            if "final_trade_decision" in final_state:
                raw_analysis = final_state.get("final_trade_decision", "")
            elif "risk_debate_state" in final_state:
                raw_analysis = final_state.get("risk_debate_state", {}).get("judge_decision", "")

        # Save the analysis result to the database
        analysis_data = {
            "company_name": symbol,
            "decision": decision.upper() if decision else "HOLD",
            "confidence": confidence or "MEDIUM",
            "risk": risk or "MEDIUM",
            "raw_analysis": raw_analysis,
            "hold_days": hold_days
        }
        db.save_single_stock_analysis(date, symbol, analysis_data, task_id=task_id)
        add_log("info", "system", f"💾 Saved analysis for {symbol} to database")

        # Save agent reports and debate data to pipeline tables
        if final_state:
            # Save individual analyst reports
            agent_reports = {}
            if final_state.get("market_report"):
                agent_reports["market"] = {"report_content": final_state["market_report"]}
            if final_state.get("news_report"):
                agent_reports["news"] = {"report_content": final_state["news_report"]}
            if final_state.get("sentiment_report"):
                agent_reports["social"] = {"report_content": final_state["sentiment_report"]}
            if final_state.get("fundamentals_report"):
                agent_reports["fundamentals"] = {"report_content": final_state["fundamentals_report"]}
            if final_state.get("trader_investment_plan"):
                agent_reports["trader"] = {"report_content": final_state["trader_investment_plan"]}

            if agent_reports:
                db.save_agent_reports_bulk(date, symbol, agent_reports, task_id=task_id)
                add_log("info", "system", f"💾 Saved {len(agent_reports)} agent reports for {symbol}")

            # Save investment debate
            invest_debate = final_state.get("investment_debate_state", {})
            if invest_debate.get("judge_decision"):
                db.save_debate_history(
                    date, symbol, "investment",
                    bull_arguments=invest_debate.get("bull_history", ""),
                    bear_arguments=invest_debate.get("bear_history", ""),
                    judge_decision=invest_debate.get("judge_decision", ""),
                    full_history=invest_debate.get("history", ""),
                    task_id=task_id,
                )

            # Save risk debate
            risk_debate = final_state.get("risk_debate_state", {})
            if risk_debate.get("judge_decision"):
                db.save_debate_history(
                    date, symbol, "risk",
                    risky_arguments=risk_debate.get("risky_history", ""),
                    safe_arguments=risk_debate.get("safe_history", ""),
                    neutral_arguments=risk_debate.get("neutral_history", ""),
                    judge_decision=risk_debate.get("judge_decision", ""),
                    full_history=risk_debate.get("history", ""),
                    task_id=task_id,
                )

        # Auto-update daily recommendation summary (counts, top_picks, stocks_to_avoid)
        db.update_daily_recommendation_summary(date, task_id=task_id)
        add_log("info", "system", f"📊 Updated daily recommendation summary for {date}")

        # Auto-trigger backtest calculation for this stock
        try:
            import backtest_service as bt
            bt_result = bt.calculate_and_save_backtest(
                date,
                symbol,
                analysis_data["decision"],
                analysis_data.get("hold_days"),
                task_id=task_id,
            )
            if bt_result:
                add_log("info", "system", f"📈 Backtest calculated for {symbol}: correct={bt_result.get('prediction_correct')}")
            else:
                add_log("info", "system", f"📈 Backtest not available yet for {symbol} (future date or no price data)")
        except Exception as bt_err:
            add_log("warning", "system", f"⚠️ Backtest calculation skipped for {symbol}: {bt_err}")

        completed_at = datetime.now().isoformat()
        running_analyses[symbol] = {
            "task_id": task_id,
            "date": date,
            "status": "completed",
            "completed_at": completed_at,
            "progress": f"Analysis complete: {decision}",
            "decision": decision
        }
        db.update_analysis_task_status(
            task_id,
            status="completed",
            total=1,
            completed=1,
            failed=0,
            completed_at=completed_at,
        )
        # Clear per-symbol step progress after completion
        try:
            from tradingagents.log_utils import symbol_progress
            symbol_progress.clear(symbol)
        except Exception:
            pass

    except Exception as e:
        error_msg = str(e) if str(e) else f"{type(e).__name__}: No details provided"
        add_log("error", "system", f"❌ Error analyzing {symbol}: {error_msg}")
        completed_at = datetime.now().isoformat()
        running_analyses[symbol] = {
            "task_id": task_id,
            "date": date,
            "status": "error",
            "completed_at": completed_at,
            "error": error_msg,
            "progress": f"Error: {error_msg[:100]}"
        }
        db.update_analysis_task_status(
            task_id,
            status="failed",
            total=1,
            completed=0,
            failed=1,
            completed_at=completed_at,
        )
        import traceback
        print(f"Analysis error for {symbol}: {type(e).__name__}: {error_msg}")
        traceback.print_exc()


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "US Stocks AI API",
        "version": "2.0.0",
        "endpoints": {
            "GET /recommendations": "Get all recommendations",
            "GET /recommendations/latest": "Get latest recommendation",
            "GET /recommendations/{date}": "Get recommendation by date",
            "GET /recommendations/{date}/{symbol}/pipeline": "Get full pipeline data for a stock",
            "GET /recommendations/{date}/{symbol}/agents": "Get agent reports for a stock",
            "GET /recommendations/{date}/{symbol}/debates": "Get debate history for a stock",
            "GET /recommendations/{date}/{symbol}/data-sources": "Get data source logs for a stock",
            "GET /recommendations/{date}/pipeline-summary": "Get pipeline summary for all stocks on a date",
            "GET /stocks/{symbol}/history": "Get stock history",
            "GET /dates": "Get all available dates",
            "POST /recommendations": "Save a new recommendation",
            "POST /pipeline": "Save pipeline data for a stock"
        }
    }


@app.get("/tasks")
async def get_tasks(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """List analysis tasks with optional filtering."""
    tasks = db.list_tasks(
        limit=limit,
        offset=offset,
        status=status,
        task_type=task_type,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "tasks": tasks,
        "count": len(tasks),
        "limit": limit,
        "offset": offset,
    }


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get details for one analysis task."""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task


@app.get("/tasks/{task_id}/recommendation")
async def get_task_recommendation(task_id: str):
    """Get recommendation payload for a specific task.

    For a newly created task, recommendation data may not exist yet while analysis
    is still pending/running. In that case, return an empty recommendation payload
    with the current task status instead of 404 so frontend polling stays stable.
    """
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    recommendation = db.get_recommendation_by_date(task_id=task_id)
    if recommendation:
        return recommendation

    return {
        "task_id": task_id,
        "date": task.get("analysis_date"),
        "analysis": {},
        "summary": {
            "total": 0,
            "buy": 0,
            "sell": 0,
            "hold": 0,
        },
        "top_picks": [],
        "stocks_to_avoid": [],
        "status": task.get("status"),
    }



@app.get("/tasks/{task_id}/{symbol}/pipeline")
async def get_task_pipeline_data(task_id: str, symbol: str):
    """Get full pipeline data for a stock in a specific task."""
    pipeline_data = db.get_full_pipeline_data(symbol=symbol.upper(), task_id=task_id)
    has_data = (
        pipeline_data.get('agent_reports') or
        pipeline_data.get('debates') or
        pipeline_data.get('pipeline_steps') or
        pipeline_data.get('data_sources')
    )

    if not has_data:
        return {
            "task_id": task_id,
            "symbol": symbol.upper(),
            "agent_reports": {},
            "debates": {},
            "pipeline_steps": [],
            "data_sources": [],
            "status": "no_data"
        }

    return {**pipeline_data, "task_id": task_id, "status": "complete"}


@app.get("/tasks/{task_id}/{symbol}/agents")
async def get_task_agent_reports(task_id: str, symbol: str):
    """Get agent reports for a stock in a specific task."""
    reports = db.get_agent_reports(symbol=symbol.upper(), task_id=task_id)
    return {
        "task_id": task_id,
        "symbol": symbol.upper(),
        "reports": reports,
        "count": len(reports)
    }


@app.get("/tasks/{task_id}/{symbol}/debates")
async def get_task_debate_history(task_id: str, symbol: str):
    """Get debate history for a stock in a specific task."""
    debates = db.get_debate_history(symbol=symbol.upper(), task_id=task_id)
    return {
        "task_id": task_id,
        "symbol": symbol.upper(),
        "debates": debates
    }


@app.get("/tasks/{task_id}/{symbol}/data-sources")
async def get_task_data_sources(task_id: str, symbol: str):
    """Get data source logs for a stock in a specific task."""
    logs = db.get_data_source_logs(symbol=symbol.upper(), task_id=task_id)
    return {
        "task_id": task_id,
        "symbol": symbol.upper(),
        "data_sources": logs,
        "count": len(logs)
    }


@app.get("/recommendations")
async def get_all_recommendations():
    """Get all daily recommendations."""
    recommendations = db.get_all_recommendations()
    return {"recommendations": recommendations, "count": len(recommendations)}


@app.get("/recommendations/latest")
async def get_latest_recommendation():
    """Get the most recent recommendation."""
    recommendation = db.get_latest_recommendation()
    if not recommendation:
        raise HTTPException(status_code=404, detail="No recommendations found")
    return recommendation


@app.get("/recommendations/{date}")
async def get_recommendation_by_date(date: str):
    """Get recommendation for a specific date (format: YYYY-MM-DD)."""
    recommendation = db.get_recommendation_by_date(date)
    if not recommendation:
        raise HTTPException(status_code=404, detail=f"No recommendation found for {date}")
    return recommendation


@app.get("/stocks/{symbol}/history")
async def get_stock_history(symbol: str):
    """Get historical recommendations for a specific stock."""
    history = db.get_stock_history(symbol.upper())
    return {"symbol": symbol.upper(), "history": history, "count": len(history)}


@app.get("/dates")
async def get_available_dates():
    """Get all dates with recommendations."""
    dates = db.get_all_dates()
    return {"dates": dates, "count": len(dates)}


@app.post("/recommendations")
async def save_recommendation(request: SaveRecommendationRequest):
    """Save a new daily recommendation."""
    try:
        db.save_recommendation(
            date=request.date,
            analysis_data=request.analysis,
            summary=request.summary,
            top_picks=request.top_picks,
            stocks_to_avoid=request.stocks_to_avoid
        )
        return {"message": f"Recommendation for {request.date} saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "database": "connected"}


# ============== Live Log Streaming Endpoint ==============

@app.get("/stream/logs")
async def stream_logs():
    """Server-Sent Events endpoint for streaming analysis logs."""
    import queue

    # Create a queue for this subscriber
    subscriber_queue = queue.Queue(maxsize=100)

    with log_lock:
        log_subscribers.append(subscriber_queue)

    async def event_generator():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'info', 'source': 'system', 'message': 'Connected to log stream', 'timestamp': datetime.now().isoformat()})}\n\n"

            # Send any recent logs from buffer
            with log_lock:
                recent_logs = list(analysis_logs)[-50:]  # Last 50 logs
            for log in recent_logs:
                yield f"data: {json.dumps(log)}\n\n"

            # Stream new logs as they arrive
            while True:
                try:
                    # Check for new logs with timeout
                    log_entry = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: subscriber_queue.get(timeout=5)
                    )
                    yield f"data: {json.dumps(log_entry)}\n\n"
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now().isoformat()})}\n\n"
                except Exception:
                    break
        finally:
            # Remove subscriber on disconnect
            with log_lock:
                if subscriber_queue in log_subscribers:
                    log_subscribers.remove(subscriber_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


# ============== Pipeline Data Endpoints ==============

@app.get("/recommendations/{date}/{symbol}/pipeline")
async def get_pipeline_data(date: str, symbol: str):
    """Get full pipeline data for a stock on a specific date."""
    pipeline_data = db.get_full_pipeline_data(date, symbol.upper())

    # Check if we have any data
    has_data = (
        pipeline_data.get('agent_reports') or
        pipeline_data.get('debates') or
        pipeline_data.get('pipeline_steps') or
        pipeline_data.get('data_sources')
    )

    if not has_data:
        # Return empty structure with mock pipeline steps if no data
        return {
            "date": date,
            "symbol": symbol.upper(),
            "agent_reports": {},
            "debates": {},
            "pipeline_steps": [],
            "data_sources": [],
            "status": "no_data"
        }

    return {**pipeline_data, "status": "complete"}


@app.get("/recommendations/{date}/{symbol}/agents")
async def get_agent_reports(date: str, symbol: str):
    """Get agent reports for a stock on a specific date."""
    reports = db.get_agent_reports(date, symbol.upper())
    return {
        "date": date,
        "symbol": symbol.upper(),
        "reports": reports,
        "count": len(reports)
    }


@app.get("/recommendations/{date}/{symbol}/debates")
async def get_debate_history(date: str, symbol: str):
    """Get debate history for a stock on a specific date."""
    debates = db.get_debate_history(date, symbol.upper())
    return {
        "date": date,
        "symbol": symbol.upper(),
        "debates": debates
    }


@app.get("/recommendations/{date}/{symbol}/data-sources")
async def get_data_sources(date: str, symbol: str):
    """Get data source logs for a stock on a specific date."""
    logs = db.get_data_source_logs(date, symbol.upper())
    return {
        "date": date,
        "symbol": symbol.upper(),
        "data_sources": logs,
        "count": len(logs)
    }


@app.get("/recommendations/{date}/pipeline-summary")
async def get_pipeline_summary(date: str):
    """Get pipeline summary for all stocks on a specific date."""
    summary = db.get_pipeline_summary_for_date(date)
    return {
        "date": date,
        "stocks": summary,
        "count": len(summary)
    }


@app.post("/pipeline")
async def save_pipeline_data(request: SavePipelineDataRequest):
    """Save pipeline data for a stock."""
    try:
        db.save_full_pipeline_data(
            date=request.date,
            symbol=request.symbol.upper(),
            pipeline_data={
                'agent_reports': request.agent_reports,
                'investment_debate': request.investment_debate,
                'risk_debate': request.risk_debate,
                'pipeline_steps': request.pipeline_steps,
                'data_sources': request.data_sources
            }
        )
        return {"message": f"Pipeline data for {request.symbol} on {request.date} saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============== Analysis Endpoints ==============

# Track bulk analysis state
bulk_analysis_state = {
    "status": "idle",  # idle, running, completed, error, cancelled
    "total": 0,
    "completed": 0,
    "failed": 0,
    "current_symbol": None,
    "started_at": None,
    "completed_at": None,
    "results": {},
    "cancelled": False  # Flag to signal cancellation
}

# Auto-analyze schedule config
SCHEDULE_FILE = Path(__file__).parent / "schedule_config.json"

def _load_schedule_config():
    """Load schedule config from JSON file."""
    if SCHEDULE_FILE.exists():
        try:
            with open(SCHEDULE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"enabled": False, "time": "09:00", "config": {}, "last_run_date": None}

def _save_schedule_config(config):
    """Persist schedule config to JSON file."""
    try:
        with open(SCHEDULE_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[AutoSchedule] Failed to save config: {e}")

schedule_config = _load_schedule_config()

# List of S&P 500 Top 50 stocks
SP500_TOP_50_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "AVGO", "LLY", "JPM",
    "TSLA", "XOM", "UNH", "V", "MA", "PG", "COST", "JNJ", "HD", "ABBV",
    "WMT", "NFLX", "CRM", "BAC", "ORCL", "CVX", "MRK", "KO", "AMD", "CSCO",
    "PEP", "ACN", "TMO", "LIN", "ADBE", "MCD", "ABT", "WFC", "GE", "IBM",
    "DHR", "QCOM", "CAT", "INTU", "DIS", "AMAT", "TXN", "NOW", "PM", "GS"
]


class BulkAnalysisRequest(BaseModel):
    deep_think_model: Optional[str] = "opus"
    quick_think_model: Optional[str] = "sonnet"
    provider: Optional[str] = "claude_subscription"
    api_key: Optional[str] = None
    max_debate_rounds: Optional[int] = 1
    parallel_workers: Optional[int] = 3


@app.post("/analyze/all")
async def run_bulk_analysis(request: Optional[BulkAnalysisRequest] = None, date: Optional[str] = None):
    """Trigger analysis for all S&P 500 Top 50 stocks. Runs in background with parallel processing."""
    global bulk_analysis_state

    # Check if bulk analysis is already running
    if bulk_analysis_state.get("status") == "running":
        return {
            "message": "Bulk analysis already running",
            "status": bulk_analysis_state
        }

    # Use today's date if not provided
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Build analysis config from request
    analysis_config = {}
    parallel_workers = 3
    if request:
        analysis_config = {
            "deep_think_model": request.deep_think_model,
            "quick_think_model": request.quick_think_model,
            "provider": request.provider,
            "api_key": request.api_key,
            "max_debate_rounds": request.max_debate_rounds
        }
        if request.parallel_workers is not None:
            parallel_workers = max(1, min(5, request.parallel_workers))

    symbols_to_analyze = list(SP500_TOP_50_SYMBOLS)
    task_id = db.create_analysis_task(
        task_type="bulk",
        analysis_date=date,
        config_json={**analysis_config, "parallel_workers": parallel_workers},
        status="pending",
        total=len(symbols_to_analyze),
        completed=0,
        failed=0,
        skipped=0,
    )

    def analyze_single_stock(symbol: str, analysis_date: str, config: dict) -> tuple:
        """Analyze a single stock and return (symbol, status, error)."""
        try:
            # Check if cancelled before starting
            if bulk_analysis_state.get("cancelled"):
                return (symbol, "cancelled", "Bulk analysis was cancelled")

            stock_task_id = db.create_analysis_task(
                task_type="single",
                analysis_date=analysis_date,
                request_symbol=symbol,
                config_json=config,
                status="pending",
                total=1,
                completed=0,
                failed=0,
                skipped=0,
            )

            run_analysis_task(stock_task_id, symbol, analysis_date, config)

            # Wait for completion with timeout
            import time
            max_wait = 600  # 10 minute timeout per stock
            waited = 0
            while waited < max_wait:
                # Check for cancellation during wait
                if bulk_analysis_state.get("cancelled"):
                    return (symbol, "cancelled", "Bulk analysis was cancelled")

                status = _get_status_by_task_id(stock_task_id)
                if not status:
                    return (symbol, "unknown", None)
                state = status.get("status")
                if state != "running" and state != "initializing":
                    return (symbol, state, None)
                time.sleep(2)
                waited += 2

            return (symbol, "timeout", "Analysis timed out after 10 minutes")

        except Exception as e:
            return (symbol, "error", str(e))

    # Start bulk analysis in background thread
    def run_bulk_parallel():
        global bulk_analysis_state
        started_at = datetime.now().isoformat()
        bulk_analysis_state = {
            "task_id": task_id,
            "status": "running",
            "total": len(symbols_to_analyze),
            "total_all": len(SP500_TOP_50_SYMBOLS),
            "skipped": 0,
            "completed": 0,
            "failed": 0,
            "current_symbols": [],
            "started_at": started_at,
            "completed_at": None,
            "results": {},
            "parallel_workers": parallel_workers,
            "cancelled": False
        }

        db.update_analysis_task_status(
            task_id,
            status="running",
            started_at=started_at,
            total=len(symbols_to_analyze),
            completed=0,
            failed=0,
            skipped=0,
        )

        with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
            future_to_symbol = {
                executor.submit(analyze_single_stock, symbol, date, analysis_config): symbol
                for symbol in symbols_to_analyze
            }

            bulk_analysis_state["current_symbols"] = list(symbols_to_analyze[:parallel_workers])

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    symbol, status, error = future.result()
                    bulk_analysis_state["results"][symbol] = status if not error else f"error: {error}"

                    if status == "completed":
                        bulk_analysis_state["completed"] += 1
                    else:
                        bulk_analysis_state["failed"] += 1

                    db.update_analysis_task_status(
                        task_id,
                        status="running" if not bulk_analysis_state.get("cancelled") else "cancelled",
                        completed=bulk_analysis_state["completed"],
                        failed=bulk_analysis_state["failed"],
                        skipped=bulk_analysis_state["skipped"],
                    )

                    remaining = [s for s in symbols_to_analyze
                                if s not in bulk_analysis_state["results"]]
                    bulk_analysis_state["current_symbols"] = remaining[:parallel_workers]

                except Exception as e:
                    bulk_analysis_state["results"][symbol] = f"error: {str(e)}"
                    bulk_analysis_state["failed"] += 1
                    db.update_analysis_task_status(
                        task_id,
                        status="running" if not bulk_analysis_state.get("cancelled") else "cancelled",
                        completed=bulk_analysis_state["completed"],
                        failed=bulk_analysis_state["failed"],
                        skipped=bulk_analysis_state["skipped"],
                    )

        final_status = "cancelled" if bulk_analysis_state.get("cancelled") else "completed"
        completed_at = datetime.now().isoformat()
        bulk_analysis_state["status"] = final_status
        bulk_analysis_state["current_symbols"] = []
        bulk_analysis_state["completed_at"] = completed_at
        db.update_analysis_task_status(
            task_id,
            status=final_status,
            completed=bulk_analysis_state["completed"],
            failed=bulk_analysis_state["failed"],
            skipped=bulk_analysis_state["skipped"],
            completed_at=completed_at,
        )

    thread = threading.Thread(target=run_bulk_parallel)
    thread.start()

    return {
        "message": f"Bulk analysis started for {len(symbols_to_analyze)} stocks ({parallel_workers} parallel workers)",
        "task_id": task_id,
        "date": date,
        "total_stocks": len(symbols_to_analyze),
        "skipped": 0,
        "parallel_workers": parallel_workers,
        "status": "started"
    }


@app.get("/analyze/all/status")
async def get_bulk_analysis_status():
    """Get the status of bulk analysis."""
    # Add backward compatibility for current_symbol (old format)
    result = dict(bulk_analysis_state)
    if "current_symbols" in result:
        result["current_symbol"] = result["current_symbols"][0] if result["current_symbols"] else None

    # Include per-stock step progress for currently-analyzing stocks
    if result.get("status") == "running" and result.get("current_symbols"):
        try:
            from tradingagents.log_utils import symbol_progress
            stock_progress = {}
            for sym in result["current_symbols"]:
                stock_progress[sym] = symbol_progress.get(sym)
            result["stock_progress"] = stock_progress
        except Exception:
            pass

    return result


@app.post("/analyze/all/cancel")
async def cancel_bulk_analysis():
    """Cancel the running bulk analysis."""
    global bulk_analysis_state

    if bulk_analysis_state.get("status") != "running":
        return {
            "message": "No bulk analysis is running",
            "status": bulk_analysis_state.get("status")
        }

    # Set the cancelled flag
    bulk_analysis_state["cancelled"] = True
    bulk_analysis_state["status"] = "cancelled"
    bulk_analysis_state["completed_at"] = datetime.now().isoformat()

    task_id = bulk_analysis_state.get("task_id")
    if task_id:
        db.update_analysis_task_status(
            task_id,
            status="cancelled",
            completed=bulk_analysis_state.get("completed", 0),
            failed=bulk_analysis_state.get("failed", 0),
            skipped=bulk_analysis_state.get("skipped", 0),
            completed_at=bulk_analysis_state["completed_at"],
        )

    return {
        "message": "Bulk analysis cancellation requested",
        "task_id": task_id,
        "completed": bulk_analysis_state.get("completed", 0),
        "total": bulk_analysis_state.get("total", 0),
        "status": "cancelled"
    }


@app.get("/analyze/running")
async def get_running_analyses():
    """Get all currently running analyses."""
    running = {k: v for k, v in running_analyses.items() if v.get("status") == "running"}
    return {
        "running": running,
        "count": len(running)
    }


class SingleAnalysisRequest(BaseModel):
    deep_think_model: Optional[str] = "opus"
    quick_think_model: Optional[str] = "sonnet"
    provider: Optional[str] = "claude_subscription"
    api_key: Optional[str] = None
    max_debate_rounds: Optional[int] = 1


@app.post("/analyze/{symbol}")
async def run_analysis(symbol: str, background_tasks: BackgroundTasks, request: Optional[SingleAnalysisRequest] = None, date: Optional[str] = None):
    """Trigger analysis for a stock. Runs in background."""
    symbol = symbol.upper()

    # Check if analysis is already running
    if symbol in running_analyses and running_analyses[symbol].get("status") == "running":
        return {
            "message": f"Analysis already running for {symbol}",
            "status": running_analyses[symbol]
        }

    # Use today's date if not provided
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # Build analysis config from request
    analysis_config = {}
    if request:
        analysis_config = {
            "deep_think_model": request.deep_think_model,
            "quick_think_model": request.quick_think_model,
            "provider": request.provider,
            "api_key": request.api_key,
            "max_debate_rounds": request.max_debate_rounds
        }

    task_id = db.create_analysis_task(
        task_type="single",
        analysis_date=date,
        request_symbol=symbol,
        config_json=analysis_config,
        status="pending",
        total=1,
        completed=0,
        failed=0,
        skipped=0,
    )

    print(
        f"[TaskLifecycle] created single task | task_id={task_id} symbol={symbol} date={date} status=pending",
        flush=True,
    )

    # Mark as initializing before worker thread starts so polling is observable
    queued_at = datetime.now().isoformat()
    running_analyses[symbol] = {
        "task_id": task_id,
        "date": date,
        "status": "initializing",
        "started_at": queued_at,
        "progress": "Task queued. Waiting for worker thread...",
        "cancelled": False,
    }
    task_to_symbol[task_id] = symbol
    db.update_analysis_task_status(
        task_id,
        status="initializing",
        started_at=queued_at,
        total=1,
        completed=0,
        failed=0,
        skipped=0,
    )

    # Start analysis in background thread
    thread = threading.Thread(
        target=run_analysis_task,
        args=(task_id, symbol, date, analysis_config),
        daemon=True,
        name=f"analysis-{symbol}-{task_id[:8]}",
    )
    thread.start()

    print(
        f"[TaskLifecycle] started analysis thread | task_id={task_id} symbol={symbol} thread={thread.name} alive={thread.is_alive()}",
        flush=True,
    )

    return {
        "message": f"Analysis started for {symbol}",
        "task_id": task_id,
        "symbol": symbol,
        "date": date,
        "status": "started"
    }


STEP_NAMES = {
    "market_analyst": "Market Analysis",
    "social_media_analyst": "Social Media Analysis",
    "news_analyst": "News Analysis",
    "fundamentals_analyst": "Fundamental Analysis",
    "bull_researcher": "Bull Research",
    "bear_researcher": "Bear Research",
    "research_manager": "Research Manager",
    "trader": "Trader Decision",
    "aggressive_analyst": "Aggressive Analysis",
    "conservative_analyst": "Conservative Analysis",
    "neutral_analyst": "Neutral Analysis",
    "risk_manager": "Risk Manager",
}

STEP_ORDER = list(STEP_NAMES.keys())


def _attach_live_progress(result: dict) -> dict:
    """Attach live pipeline step progress to a task/symbol status payload."""
    if result.get("status") not in ("running", "initializing"):
        return result

    symbol = result.get("symbol")

    # Preferred source: step_timer with per-step statuses/durations
    try:
        from tradingagents.log_utils import step_timer

        steps = step_timer.get_steps()
        if steps:
            completed = [k for k, v in steps.items() if v.get("status") == "completed"]
            running = [k for k, v in steps.items() if v.get("status") == "running"]

            if running:
                current_step = STEP_NAMES.get(running[0], running[0])
                result["progress"] = f"Step {len(completed)+1}/{len(STEP_ORDER)}: {current_step}..."
            elif completed:
                last_step = STEP_NAMES.get(completed[-1], completed[-1])
                result["progress"] = f"Step {len(completed)}/{len(STEP_ORDER)}: {last_step} done"

            result["steps_completed"] = len(completed)
            result["steps_running"] = [STEP_NAMES.get(s, s) for s in running]
            result["steps_total"] = len(STEP_ORDER)
            result["pipeline_steps"] = {
                step_id: {
                    "status": entry.get("status"),
                    "duration_ms": entry.get("duration_ms"),
                }
                for step_id, entry in steps.items()
            }
            return result
    except Exception:
        pass

    # Fallback source: per-symbol coarse progress tracker
    if symbol:
        try:
            from tradingagents.log_utils import symbol_progress

            sp = symbol_progress.get(symbol)
            done = int(sp.get("done", 0))
            current = sp.get("current")

            pipeline_steps = {name: {"status": "pending"} for name in STEP_ORDER}
            if current in pipeline_steps:
                pipeline_steps[current]["status"] = "running"

            result["steps_completed"] = done
            result["steps_running"] = [STEP_NAMES.get(current, current)] if current else []
            result["steps_total"] = len(STEP_ORDER)
            result["pipeline_steps"] = pipeline_steps
            if current:
                result["progress"] = f"Step {min(done + 1, len(STEP_ORDER))}/{len(STEP_ORDER)}: {STEP_NAMES.get(current, current)}..."
            else:
                result["progress"] = result.get("progress") or "Initializing analysis pipeline..."
        except Exception:
            pass

    return result


@app.get("/analyze/{symbol}/status")
async def get_analysis_status(symbol: str):
    """Get the status of a running or completed analysis, including live pipeline step progress."""
    symbol = symbol.upper()

    if symbol not in running_analyses:
        return {
            "symbol": symbol,
            "status": "not_started",
            "message": "No analysis has been run for this stock"
        }

    result = {
        "symbol": symbol,
        **running_analyses[symbol]
    }

    result = _attach_live_progress(result)
    return result


@app.get("/analyze/task/{task_id}/status")
async def get_analysis_status_by_task(task_id: str):
    """Get status for a specific analysis task_id."""
    result = _get_status_by_task_id(task_id)
    if not result:
        print(f"[TaskStatus] task not found | task_id={task_id}", flush=True)
        return {
            "task_id": task_id,
            "status": "not_found",
            "message": "No analysis task found"
        }

    result = _attach_live_progress(result)

    print(
        f"[TaskStatus] polled | task_id={task_id} symbol={result.get('symbol')} status={result.get('status')} progress={result.get('progress')} steps={result.get('steps_completed', 0)}/{result.get('steps_total', 0)} running={result.get('steps_running', [])}",
        flush=True,
    )
    return result


@app.post("/analyze/{symbol}/cancel")
async def cancel_analysis(symbol: str):
    """Cancel a running analysis for a stock."""
    symbol = symbol.upper()

    if symbol not in running_analyses:
        return {"message": f"No analysis found for {symbol}", "status": "not_found"}

    current_status = running_analyses[symbol].get("status")
    if current_status not in ("running", "initializing"):
        return {"message": f"Analysis for {symbol} is not running (status: {current_status})", "status": current_status}

    # Set cancellation flag — the background thread checks this
    running_analyses[symbol]["cancelled"] = True
    running_analyses[symbol]["status"] = "cancelled"
    running_analyses[symbol]["progress"] = "Cancellation requested..."
    running_analyses[symbol]["completed_at"] = datetime.now().isoformat()

    task_id = running_analyses[symbol].get("task_id")
    if task_id:
        db.update_analysis_task_status(
            task_id,
            status="cancelled",
            completed=0,
            failed=1,
            completed_at=running_analyses[symbol]["completed_at"],
        )

    add_log("info", "system", f"🛑 Cancellation requested for {symbol}")

    return {
        "message": f"Cancellation requested for {symbol}",
        "task_id": task_id,
        "symbol": symbol,
        "status": "cancelled"
    }


# ============== History Bundle Endpoint ==============

# In-memory cache for S&P 500 index prices (fetched once, refreshed lazily)
_sp500_cache = {"prices": {}, "fetched_at": None}

def _fetch_sp500_prices_sync():
    """Fetch S&P 500 index prices (called once and cached)."""
    try:
        import yfinance as yf
        from datetime import timedelta

        dates = db.get_all_dates()
        if not dates:
            return {}

        start_date = (datetime.strptime(min(dates), "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (datetime.strptime(max(dates), "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")

        sp500 = yf.Ticker("^GSPC")
        hist = sp500.history(start=start_date, end=end_date, interval="1d")

        prices = {}
        for idx, row in hist.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            prices[date_str] = round(float(row['Close']), 2)
        return prices
    except Exception:
        return {}


@app.get("/history/bundle")
async def get_history_bundle():
    """Return ALL data the History page needs in a single response.

    Combines: recommendations + all backtest results + accuracy metrics.
    Everything comes from SQLite (instant), no yfinance calls.
    S&P 500 prices are served from cache.
    """
    recommendations = db.get_all_recommendations()
    backtest_by_date = db.get_all_backtest_results_grouped()
    accuracy = db.calculate_accuracy_metrics()

    # Serve S&P 500 from cache, refresh in background if stale
    sp500_prices = _sp500_cache.get("prices", {})
    if not _sp500_cache.get("fetched_at"):
        # First request — return empty, trigger background fetch
        def bg_fetch():
            prices = _fetch_sp500_prices_sync()
            _sp500_cache["prices"] = prices
            _sp500_cache["fetched_at"] = datetime.now().isoformat()
        thread = threading.Thread(target=bg_fetch, daemon=True)
        thread.start()
    else:
        sp500_prices = _sp500_cache["prices"]

    return {
        "recommendations": recommendations,
        "backtest_by_date": backtest_by_date,
        "accuracy": accuracy,
        "sp500_prices": sp500_prices,
    }


# ============== Backtest Endpoints ==============
# NOTE: Static routes must come BEFORE parameterized routes to avoid
# "accuracy" being matched as a {date} parameter.

@app.get("/backtest/accuracy")
async def get_accuracy_metrics():
    """Get overall backtest accuracy metrics."""
    metrics = db.calculate_accuracy_metrics()
    return metrics


@app.get("/backtest/{date}/detailed")
async def get_detailed_backtest(date: str, task_id: Optional[str] = None):
    """Get enriched backtest data with live prices, formulas, agent reports, and debate summaries."""
    import yfinance as yf

    rec = db.get_recommendation_by_date(date=date, task_id=task_id)
    if not rec or 'analysis' not in rec:
        return {"date": date, "task_id": task_id, "total_stocks": 0, "stocks": []}

    analysis = rec['analysis']
    effective_date = rec.get('date') or date
    effective_task_id = task_id or rec.get('task_id')
    backtest_results = db.get_backtest_results_by_date(date=effective_date, task_id=effective_task_id)
    bt_by_symbol = {r['symbol']: r for r in backtest_results}

    pred_date = datetime.strptime(effective_date, '%Y-%m-%d')
    today = datetime.now()


    # Collect symbols that need live prices (active hold periods)
    symbols_needing_live = []
    for symbol, stock_data in analysis.items():
        hold_days = stock_data.get('hold_days') or 0
        hold_end = pred_date + timedelta(days=hold_days) if hold_days > 0 else pred_date + timedelta(days=1)
        if today < hold_end:
            symbols_needing_live.append(symbol)

    # Batch-fetch live prices for active holds
    live_prices = {}
    if symbols_needing_live:
        def fetch_live_batch():
            for sym in symbols_needing_live:
                try:
                    yf_sym = sym
                    t = yf.Ticker(yf_sym)
                    hist = t.history(period='1d')
                    if not hist.empty:
                        live_prices[sym] = round(float(hist['Close'].iloc[-1]), 2)
                except Exception:
                    pass
        fetch_live_batch()

    stocks = []
    for symbol, stock_data in analysis.items():
        decision = stock_data.get('decision', 'HOLD')
        confidence = stock_data.get('confidence', 'MEDIUM')
        risk = stock_data.get('risk', 'MEDIUM')
        hold_days = stock_data.get('hold_days') or 0
        raw_analysis = stock_data.get('raw_analysis', '')

        bt = bt_by_symbol.get(symbol, {})
        price_pred = bt.get('price_at_prediction')

        # Calculate hold period status
        hold_end_date = pred_date + timedelta(days=hold_days) if hold_days > 0 else pred_date + timedelta(days=1)
        days_elapsed = (today - pred_date).days
        hold_period_active = today < hold_end_date and hold_days > 0

        # Determine display price and return
        price_current = live_prices.get(symbol)
        price_at_hold_end = None
        return_current = None
        return_at_hold = bt.get('return_at_hold')

        if price_pred:
            if hold_period_active and price_current:
                return_current = round(((price_current - price_pred) / price_pred) * 100, 2)
            elif not hold_period_active:
                # Hold completed — use stored data
                if return_at_hold is not None:
                    price_at_hold_end = round(price_pred * (1 + return_at_hold / 100), 2)
                elif bt.get('return_1d') is not None:
                    return_current = bt['return_1d']

        # Build formula string
        formula = ""
        if price_pred:
            if hold_period_active and price_current:
                ret = return_current or 0
                sign = "+" if ret >= 0 else ""
                formula = f"Return = (${price_current} - ${price_pred}) / ${price_pred} × 100 = {sign}{ret}%"
            elif return_at_hold is not None:
                p_end = price_at_hold_end or round(price_pred * (1 + return_at_hold / 100), 2)
                sign = "+" if return_at_hold >= 0 else ""
                formula = f"Return = (${p_end} - ${price_pred}) / ${price_pred} × 100 = {sign}{return_at_hold}%"
            elif bt.get('return_1d') is not None:
                p_1d = bt.get('price_1d_later', 0)
                r_1d = bt['return_1d']
                sign = "+" if r_1d >= 0 else ""
                formula = f"Return = (${p_1d} - ${price_pred}) / ${price_pred} × 100 = {sign}{r_1d}%"

        # Prediction correctness
        prediction_correct = bt.get('prediction_correct')
        if hold_period_active:
            prediction_correct = None  # Can't judge while hold is active

        # Agent reports (condensed)
        agent_summary = {}
        try:
            reports = db.get_agent_reports(date=effective_date, symbol=symbol, task_id=effective_task_id)
            for agent_type, report_data in reports.items():
                content = report_data.get('report_content', '')
                # Take first 300 chars as summary
                agent_summary[agent_type] = content[:300] + ('...' if len(content) > 300 else '')
        except Exception:
            pass

        # Debate summary
        debate_summary = {}
        try:
            debates = db.get_debate_history(date=effective_date, symbol=symbol, task_id=effective_task_id)
            for debate_type, debate_data in debates.items():
                judge = debate_data.get('judge_decision', '')
                judge_short = judge[:200] + ('...' if len(judge) > 200 else '') if judge else ''
                debate_summary[debate_type] = judge_short
        except Exception:
            pass

        stocks.append({
            "symbol": symbol,
            "company_name": stock_data.get('company_name', symbol),
            "rank": stock_data.get('rank'),
            "decision": decision,
            "confidence": confidence,
            "risk": risk,
            "hold_days": hold_days,
            "hold_days_elapsed": min(days_elapsed, hold_days) if hold_days > 0 else days_elapsed,
            "hold_period_active": hold_period_active,
            "price_at_prediction": price_pred,
            "price_current": price_current,
            "price_at_hold_end": price_at_hold_end,
            "return_current": return_current,
            "return_at_hold": return_at_hold,
            "prediction_correct": prediction_correct,
            "formula": formula,
            "raw_analysis": raw_analysis[:500] if raw_analysis else '',
            "agent_summary": agent_summary,
            "debate_summary": debate_summary,
        })

    # Sort by rank
    stocks.sort(key=lambda s: s.get('rank') or 999)

    return {
        "date": effective_date,
        "task_id": effective_task_id,
        "total_stocks": len(stocks),
        "stocks": stocks,
    }


@app.get("/backtest/{date}/{symbol}")
async def get_backtest_result(date: str, symbol: str, task_id: Optional[str] = None):
    """Get backtest result for a specific stock and date/task.

    Returns pre-calculated results only (no on-demand yfinance fetching)
    to avoid blocking the event loop.
    """
    result = db.get_backtest_result(date=date, symbol=symbol.upper(), task_id=task_id)
    if not result:
        return {'available': False, 'reason': 'Backtest not yet calculated'}

    return {
        'available': True,
        'task_id': result.get('task_id') or task_id,
        'prediction_correct': result['prediction_correct'],
        'actual_return_1d': result['return_1d'],
        'actual_return_1w': result['return_1w'],
        'actual_return_1m': result['return_1m'],
        'return_at_hold': result.get('return_at_hold'),
        'hold_days': result.get('hold_days'),
        'price_at_prediction': result['price_at_prediction'],
        'current_price': result.get('price_1m_later') or result.get('price_1w_later'),
    }


@app.get("/backtest/{date}")
async def get_backtest_results_for_date(date: str, task_id: Optional[str] = None):
    """Get all backtest results for a specific date/task."""
    results = db.get_backtest_results_by_date(date=date, task_id=task_id)
    return {"date": date, "task_id": task_id, "results": results}


@app.post("/backtest/{date}/calculate")
async def calculate_backtest_for_date(date: str, task_id: Optional[str] = None):
    """Calculate backtest for all recommendations on a date/task (runs in background thread)."""
    import backtest_service as bt

    # Run calculation in a separate thread to avoid blocking the event loop
    def run_backtest():
        try:
            bt.backtest_all_recommendations_for_date(date=date, task_id=task_id)
        except Exception as e:
            print(f"Backtest calculation error for {date} (task={task_id}): {e}")

    thread = threading.Thread(target=run_backtest)
    thread.start()
    return {
        "status": "started",
        "date": date,
        "task_id": task_id,
        "message": "Backtest calculation started in background"
    }


# ============== Stock Price History Endpoint ==============

@app.get("/stocks/{symbol}/prices")
async def get_stock_price_history(symbol: str, days: int = 90):
    """Get real historical closing prices for a stock from yfinance."""
    try:
        import yfinance as yf
        from datetime import timedelta

        yf_symbol = symbol
        ticker = yf.Ticker(yf_symbol)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        hist = ticker.history(start=start_date.strftime('%Y-%m-%d'),
                             end=end_date.strftime('%Y-%m-%d'))

        if hist.empty:
            return {"symbol": symbol, "prices": [], "error": "No price data found"}

        prices = [
            {"date": idx.strftime('%Y-%m-%d'), "price": round(float(row['Close']), 2)}
            for idx, row in hist.iterrows()
        ]

        return {"symbol": symbol, "prices": prices}
    except ImportError:
        return {"symbol": symbol, "prices": [], "error": "yfinance not installed"}
    except Exception as e:
        return {"symbol": symbol, "prices": [], "error": str(e)}


# ============== S&P 500 Index Endpoint ==============

@app.get("/sp500/history")
async def get_sp500_history():
    """Get S&P 500 index closing prices for recommendation date range."""
    try:
        import yfinance as yf
        from datetime import timedelta

        # Get the date range from our recommendations
        dates = db.get_all_dates()
        if not dates:
            return {"dates": [], "prices": {}}

        # Get date range with buffer for daily return calculation
        start_date = (datetime.strptime(min(dates), "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = (datetime.strptime(max(dates), "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")

        # Fetch ^GSPC data
        sp500 = yf.Ticker("^GSPC")
        hist = sp500.history(start=start_date, end=end_date, interval="1d")

        prices = {}
        for idx, row in hist.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            prices[date_str] = round(float(row['Close']), 2)

        return {"dates": sorted(prices.keys()), "prices": prices}
    except ImportError:
        return {"dates": [], "prices": {}, "error": "yfinance not installed"}
    except Exception as e:
        return {"dates": [], "prices": {}, "error": str(e)}


# ============== Schedule Endpoints ==============

class ScheduleRequest(BaseModel):
    enabled: bool = False
    time: str = "09:00"
    timezone: str = "America/New_York"
    config: dict = {}

@app.post("/settings/schedule")
async def set_schedule(request: ScheduleRequest):
    """Set the auto-analyze schedule."""
    global schedule_config
    schedule_config["enabled"] = request.enabled
    schedule_config["time"] = request.time
    schedule_config["timezone"] = request.timezone
    schedule_config["config"] = request.config
    _save_schedule_config(schedule_config)
    status = "enabled" if request.enabled else "disabled"
    print(f"[AutoSchedule] Schedule updated: {request.time} {request.timezone} ({status})")
    return {"status": "ok", "message": f"Schedule {status} at {request.time} {request.timezone}"}

@app.get("/settings/schedule")
async def get_schedule():
    """Get the current auto-analyze schedule."""
    return {
        "enabled": schedule_config.get("enabled", False),
        "time": schedule_config.get("time", "09:00"),
        "timezone": schedule_config.get("timezone", "Asia/Kolkata"),
        "config": schedule_config.get("config", {}),
        "last_run_date": schedule_config.get("last_run_date"),
    }


# ============== Scheduler Thread ==============

def _auto_analyze_scheduler():
    """Background thread that triggers Analyze All at the scheduled time daily."""
    from zoneinfo import ZoneInfo
    global schedule_config, bulk_analysis_state
    print("[AutoSchedule] Scheduler thread started")

    while True:
        try:
            time.sleep(30)

            if not schedule_config.get("enabled"):
                continue

            # Get current time in the configured timezone
            tz_name = schedule_config.get("timezone", "Asia/Kolkata")
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo("Asia/Kolkata")

            now = datetime.now(tz)
            scheduled_time = schedule_config.get("time", "09:00")
            today_str = now.strftime("%Y-%m-%d")

            # Already ran today (in the configured timezone)?
            if schedule_config.get("last_run_date") == today_str:
                continue

            # Parse scheduled hour:minute
            try:
                sched_hour, sched_minute = map(int, scheduled_time.split(":"))
            except (ValueError, AttributeError):
                continue

            # Check if we're within a 2-minute window of the scheduled time
            current_minutes = now.hour * 60 + now.minute
            scheduled_minutes = sched_hour * 60 + sched_minute
            if abs(current_minutes - scheduled_minutes) > 1:
                continue

            # Don't trigger if already running
            if bulk_analysis_state.get("status") == "running":
                print(f"[AutoSchedule] Skipping — bulk analysis already running")
                continue

            print(f"[AutoSchedule] Triggering daily analysis at {scheduled_time} {tz_name}")
            schedule_config["last_run_date"] = today_str
            _save_schedule_config(schedule_config)

            # Build analysis config
            config = schedule_config.get("config", {})
            analysis_config = {
                "deep_think_model": config.get("deep_think_model", "opus"),
                "quick_think_model": config.get("quick_think_model", "sonnet"),
                "provider": config.get("provider", "claude_subscription"),
                "api_key": config.get("api_key"),
                "max_debate_rounds": config.get("max_debate_rounds", 1),
            }
            parallel_workers = max(1, min(5, config.get("parallel_workers", 3)))

            # Same logic as POST /analyze/all
            analysis_date = today_str
            symbols_to_analyze = list(SP500_TOP_50_SYMBOLS)
            bulk_task_id = db.create_analysis_task(
                task_type="bulk",
                analysis_date=analysis_date,
                config_json={**analysis_config, "parallel_workers": parallel_workers, "source": "scheduler"},
                status="pending",
                total=len(symbols_to_analyze),
                completed=0,
                failed=0,
                skipped=0,
            )

            if not symbols_to_analyze:
                print(f"[AutoSchedule] No symbols configured for {analysis_date}")
                continue

            def run_auto_bulk():
                global bulk_analysis_state
                started_at = datetime.now().isoformat()
                bulk_analysis_state = {
                    "task_id": bulk_task_id,
                    "status": "running",
                    "total": len(symbols_to_analyze),
                    "total_all": len(SP500_TOP_50_SYMBOLS),
                    "skipped": 0,
                    "completed": 0,
                    "failed": 0,
                    "current_symbols": [],
                    "started_at": started_at,
                    "completed_at": None,
                    "results": {},
                    "parallel_workers": parallel_workers,
                    "cancelled": False,
                }

                db.update_analysis_task_status(
                    bulk_task_id,
                    status="running",
                    started_at=started_at,
                    total=len(symbols_to_analyze),
                    completed=0,
                    failed=0,
                    skipped=0,
                )

                with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                    def analyze_one(symbol):
                        try:
                            if bulk_analysis_state.get("cancelled"):
                                return (symbol, "cancelled", None)

                            stock_task_id = db.create_analysis_task(
                                task_type="single",
                                analysis_date=analysis_date,
                                request_symbol=symbol,
                                config_json=analysis_config,
                                status="pending",
                                total=1,
                                completed=0,
                                failed=0,
                                skipped=0,
                            )

                            run_analysis_task(stock_task_id, symbol, analysis_date, analysis_config)
                            max_wait = 600
                            waited = 0
                            while waited < max_wait:
                                if bulk_analysis_state.get("cancelled"):
                                    return (symbol, "cancelled", None)
                                status_data = _get_status_by_task_id(stock_task_id)
                                if not status_data:
                                    return (symbol, "unknown", None)
                                status = status_data.get("status")
                                if status not in ("running", "initializing"):
                                    return (symbol, status, None)
                                time.sleep(2)
                                waited += 2
                            return (symbol, "timeout", None)
                        except Exception as e:
                            return (symbol, "error", str(e))

                    future_to_sym = {
                        executor.submit(analyze_one, sym): sym
                        for sym in symbols_to_analyze
                    }
                    bulk_analysis_state["current_symbols"] = list(symbols_to_analyze[:parallel_workers])

                    for future in as_completed(future_to_sym):
                        sym = future_to_sym[future]
                        try:
                            sym, status, error = future.result()
                            bulk_analysis_state["results"][sym] = status if not error else f"error: {error}"
                            if status == "completed":
                                bulk_analysis_state["completed"] += 1
                            else:
                                bulk_analysis_state["failed"] += 1

                            db.update_analysis_task_status(
                                bulk_task_id,
                                status="running" if not bulk_analysis_state.get("cancelled") else "cancelled",
                                completed=bulk_analysis_state["completed"],
                                failed=bulk_analysis_state["failed"],
                                skipped=bulk_analysis_state["skipped"],
                            )

                            remaining = [s for s in symbols_to_analyze if s not in bulk_analysis_state["results"]]
                            bulk_analysis_state["current_symbols"] = remaining[:parallel_workers]
                        except Exception as e:
                            bulk_analysis_state["results"][sym] = f"error: {str(e)}"
                            bulk_analysis_state["failed"] += 1
                            db.update_analysis_task_status(
                                bulk_task_id,
                                status="running" if not bulk_analysis_state.get("cancelled") else "cancelled",
                                completed=bulk_analysis_state["completed"],
                                failed=bulk_analysis_state["failed"],
                                skipped=bulk_analysis_state["skipped"],
                            )

                final_status = "cancelled" if bulk_analysis_state.get("cancelled") else "completed"
                completed_at = datetime.now().isoformat()
                bulk_analysis_state["status"] = final_status
                bulk_analysis_state["current_symbols"] = []
                bulk_analysis_state["completed_at"] = completed_at

                db.update_analysis_task_status(
                    bulk_task_id,
                    status=final_status,
                    completed=bulk_analysis_state["completed"],
                    failed=bulk_analysis_state["failed"],
                    skipped=bulk_analysis_state["skipped"],
                    completed_at=completed_at,
                )

                print(f"[AutoSchedule] Daily analysis completed: {bulk_analysis_state['completed']} succeeded, {bulk_analysis_state['failed']} failed")


            threading.Thread(target=run_auto_bulk, daemon=True).start()

        except Exception as e:
            print(f"[AutoSchedule] Scheduler error: {e}")
            time.sleep(60)


@app.on_event("startup")
async def startup_event():
    """Rebuild daily_recommendations and trigger backtest calculations at startup."""
    db.init_db()
    db.rebuild_all_daily_recommendations()

    # Start auto-analyze scheduler
    threading.Thread(target=_auto_analyze_scheduler, daemon=True).start()

    # Warm S&P 500 cache in background
    def warm_sp500_cache():
        prices = _fetch_sp500_prices_sync()
        _sp500_cache["prices"] = prices
        _sp500_cache["fetched_at"] = datetime.now().isoformat()
        print(f"[S&P500] Cached {len(prices)} index prices")
    threading.Thread(target=warm_sp500_cache, daemon=True).start()

    # Trigger backtest calculation for all dates in background
    def startup_backtest():
        import backtest_service as bt
        dates = db.get_all_dates()
        for date in dates:
            existing = db.get_backtest_results_by_date(date=date)
            rec = db.get_recommendation_by_date(date=date)
            expected_count = len(rec.get('analysis', {})) if rec else 0
            if len(existing) < expected_count:
                print(f"[Backtest] Calculating for {date} ({len(existing)}/{expected_count} done)...")
                try:
                    bt.backtest_all_recommendations_for_date(date=date)
                except Exception as e:
                    print(f"[Backtest] Error for {date}: {e}")

    thread = threading.Thread(target=startup_backtest, daemon=True)
    thread.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

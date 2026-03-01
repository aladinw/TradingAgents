# SQLite -> PostgreSQL 表结构整理（含索引与中文注释）

本文基于当前代码中的 SQLite DDL 定义整理，并给出等价的 PostgreSQL 建表与索引方案。

- 来源文件：
  - `frontend/backend/database.py`
  - `tradingagents/portfolio/persistence.py`
- 当前仓库实际发现的 SQLite 文件：
  - `frontend/backend/recommendations.db`
- 代码中还定义了运行时可能创建的组合数据库：
  - `portfolio.db`（默认位于 `./portfolio_data/`）

---

## 1. 库与表总览

### 1.1 推荐分析库（对应 `recommendations.db`）

表：
1. `daily_recommendations`
2. `stock_analysis`
3. `agent_reports`
4. `debate_history`
5. `pipeline_steps`
6. `data_source_logs`
7. `backtest_results`

索引：
- `idx_stock_analysis_date` on `stock_analysis(date)`
- `idx_stock_analysis_symbol` on `stock_analysis(symbol)`
- `idx_agent_reports_date_symbol` on `agent_reports(date, symbol)`
- `idx_debate_history_date_symbol` on `debate_history(date, symbol)`
- `idx_pipeline_steps_date_symbol` on `pipeline_steps(date, symbol)`
- `idx_data_source_logs_date_symbol` on `data_source_logs(date, symbol)`
- `idx_backtest_results_date` on `backtest_results(date)`

---

### 1.2 组合持久化库（对应 `portfolio.db`）

表：
1. `portfolio_snapshots`
2. `positions`
3. `trades`

索引：
- `idx_positions_snapshot` on `positions(snapshot_id)`
- `idx_trades_snapshot` on `trades(snapshot_id)`
- `idx_trades_ticker` on `trades(ticker)`

---

## 2. PostgreSQL DDL（含中文注释）

> 说明：以下 DDL 保持与当前 SQLite 语义尽可能一致。
> 字段 `date/timestamp/created_at` 在 SQLite 中为 `TEXT`，迁移到 PG 时可先保留 `TEXT` 以保证兼容；后续可按需要升级为 `DATE/TIMESTAMPTZ`。

```sql
-- =========================
-- A) 推荐分析相关表（recommendations.db）
-- =========================

CREATE TABLE IF NOT EXISTS daily_recommendations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    summary_total INTEGER,
    summary_buy INTEGER,
    summary_sell INTEGER,
    summary_hold INTEGER,
    top_picks TEXT,
    stocks_to_avoid TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE daily_recommendations IS '每日推荐汇总表';
COMMENT ON COLUMN daily_recommendations.id IS '主键ID';
COMMENT ON COLUMN daily_recommendations.date IS '交易日期（字符串，通常YYYY-MM-DD）';
COMMENT ON COLUMN daily_recommendations.summary_total IS '当日分析股票总数';
COMMENT ON COLUMN daily_recommendations.summary_buy IS 'BUY数量';
COMMENT ON COLUMN daily_recommendations.summary_sell IS 'SELL数量';
COMMENT ON COLUMN daily_recommendations.summary_hold IS 'HOLD数量';
COMMENT ON COLUMN daily_recommendations.top_picks IS '重点推荐股票（通常为JSON字符串）';
COMMENT ON COLUMN daily_recommendations.stocks_to_avoid IS '建议规避股票（通常为JSON字符串）';
COMMENT ON COLUMN daily_recommendations.created_at IS '记录创建时间';


CREATE TABLE IF NOT EXISTS stock_analysis (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    company_name TEXT,
    decision TEXT,
    confidence TEXT,
    risk TEXT,
    raw_analysis TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    hold_days INTEGER,
    rank INTEGER,
    CONSTRAINT uq_stock_analysis_date_symbol UNIQUE (date, symbol)
);

COMMENT ON TABLE stock_analysis IS '单只股票分析结果表';
COMMENT ON COLUMN stock_analysis.id IS '主键ID';
COMMENT ON COLUMN stock_analysis.date IS '分析日期';
COMMENT ON COLUMN stock_analysis.symbol IS '股票代码';
COMMENT ON COLUMN stock_analysis.company_name IS '公司名称';
COMMENT ON COLUMN stock_analysis.decision IS '决策结果（BUY/SELL/HOLD）';
COMMENT ON COLUMN stock_analysis.confidence IS '置信度';
COMMENT ON COLUMN stock_analysis.risk IS '风险等级';
COMMENT ON COLUMN stock_analysis.raw_analysis IS '原始分析文本';
COMMENT ON COLUMN stock_analysis.created_at IS '创建时间';
COMMENT ON COLUMN stock_analysis.hold_days IS '建议持有天数';
COMMENT ON COLUMN stock_analysis.rank IS '当日排序名次';


CREATE TABLE IF NOT EXISTS agent_reports (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    agent_type TEXT NOT NULL,
    report_content TEXT,
    data_sources_used TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_agent_reports_date_symbol_agent UNIQUE (date, symbol, agent_type)
);

COMMENT ON TABLE agent_reports IS '各分析Agent报告表';
COMMENT ON COLUMN agent_reports.id IS '主键ID';
COMMENT ON COLUMN agent_reports.date IS '分析日期';
COMMENT ON COLUMN agent_reports.symbol IS '股票代码';
COMMENT ON COLUMN agent_reports.agent_type IS 'Agent类型';
COMMENT ON COLUMN agent_reports.report_content IS '报告内容';
COMMENT ON COLUMN agent_reports.data_sources_used IS '使用的数据源（通常为JSON字符串）';
COMMENT ON COLUMN agent_reports.created_at IS '创建时间';


CREATE TABLE IF NOT EXISTS debate_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    debate_type TEXT NOT NULL,
    bull_arguments TEXT,
    bear_arguments TEXT,
    risky_arguments TEXT,
    safe_arguments TEXT,
    neutral_arguments TEXT,
    judge_decision TEXT,
    full_history TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_debate_history_date_symbol_type UNIQUE (date, symbol, debate_type)
);

COMMENT ON TABLE debate_history IS '投资/风险辩论历史表';
COMMENT ON COLUMN debate_history.id IS '主键ID';
COMMENT ON COLUMN debate_history.date IS '分析日期';
COMMENT ON COLUMN debate_history.symbol IS '股票代码';
COMMENT ON COLUMN debate_history.debate_type IS '辩论类型（investment/risk）';
COMMENT ON COLUMN debate_history.bull_arguments IS '看多观点';
COMMENT ON COLUMN debate_history.bear_arguments IS '看空观点';
COMMENT ON COLUMN debate_history.risky_arguments IS '激进风险观点';
COMMENT ON COLUMN debate_history.safe_arguments IS '保守风险观点';
COMMENT ON COLUMN debate_history.neutral_arguments IS '中性风险观点';
COMMENT ON COLUMN debate_history.judge_decision IS '裁决结论';
COMMENT ON COLUMN debate_history.full_history IS '完整辩论历史';
COMMENT ON COLUMN debate_history.created_at IS '创建时间';


CREATE TABLE IF NOT EXISTS pipeline_steps (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    step_number INTEGER,
    step_name TEXT,
    status TEXT,
    started_at TEXT,
    completed_at TEXT,
    duration_ms INTEGER,
    output_summary TEXT,
    step_details TEXT,
    CONSTRAINT uq_pipeline_steps_date_symbol_step UNIQUE (date, symbol, step_number)
);

COMMENT ON TABLE pipeline_steps IS '流水线执行步骤日志表';
COMMENT ON COLUMN pipeline_steps.id IS '主键ID';
COMMENT ON COLUMN pipeline_steps.date IS '分析日期';
COMMENT ON COLUMN pipeline_steps.symbol IS '股票代码';
COMMENT ON COLUMN pipeline_steps.step_number IS '步骤序号';
COMMENT ON COLUMN pipeline_steps.step_name IS '步骤名称';
COMMENT ON COLUMN pipeline_steps.status IS '执行状态';
COMMENT ON COLUMN pipeline_steps.started_at IS '开始时间';
COMMENT ON COLUMN pipeline_steps.completed_at IS '完成时间';
COMMENT ON COLUMN pipeline_steps.duration_ms IS '耗时（毫秒）';
COMMENT ON COLUMN pipeline_steps.output_summary IS '输出摘要';
COMMENT ON COLUMN pipeline_steps.step_details IS '步骤详细信息';


CREATE TABLE IF NOT EXISTS data_source_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    source_type TEXT,
    source_name TEXT,
    method TEXT,
    args TEXT,
    data_fetched TEXT,
    fetch_timestamp TEXT,
    success INTEGER DEFAULT 1,
    error_message TEXT
);

COMMENT ON TABLE data_source_logs IS '数据源抓取日志表';
COMMENT ON COLUMN data_source_logs.id IS '主键ID';
COMMENT ON COLUMN data_source_logs.date IS '分析日期';
COMMENT ON COLUMN data_source_logs.symbol IS '股票代码';
COMMENT ON COLUMN data_source_logs.source_type IS '数据源类型';
COMMENT ON COLUMN data_source_logs.source_name IS '数据源名称';
COMMENT ON COLUMN data_source_logs.method IS '抓取方法/函数';
COMMENT ON COLUMN data_source_logs.args IS '调用参数（通常为JSON字符串）';
COMMENT ON COLUMN data_source_logs.data_fetched IS '抓取到的原始数据';
COMMENT ON COLUMN data_source_logs.fetch_timestamp IS '抓取时间';
COMMENT ON COLUMN data_source_logs.success IS '是否成功（1成功，0失败）';
COMMENT ON COLUMN data_source_logs.error_message IS '错误信息';


CREATE TABLE IF NOT EXISTS backtest_results (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    decision TEXT,
    price_at_prediction DOUBLE PRECISION,
    price_1d_later DOUBLE PRECISION,
    price_1w_later DOUBLE PRECISION,
    price_1m_later DOUBLE PRECISION,
    return_1d DOUBLE PRECISION,
    return_1w DOUBLE PRECISION,
    return_1m DOUBLE PRECISION,
    prediction_correct INTEGER,
    calculated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    hold_days INTEGER,
    return_at_hold DOUBLE PRECISION,
    CONSTRAINT uq_backtest_results_date_symbol UNIQUE (date, symbol)
);

COMMENT ON TABLE backtest_results IS '回测结果表';
COMMENT ON COLUMN backtest_results.id IS '主键ID';
COMMENT ON COLUMN backtest_results.date IS '分析日期';
COMMENT ON COLUMN backtest_results.symbol IS '股票代码';
COMMENT ON COLUMN backtest_results.decision IS '预测决策（BUY/SELL/HOLD）';
COMMENT ON COLUMN backtest_results.price_at_prediction IS '预测时价格';
COMMENT ON COLUMN backtest_results.price_1d_later IS '1天后价格';
COMMENT ON COLUMN backtest_results.price_1w_later IS '1周后价格';
COMMENT ON COLUMN backtest_results.price_1m_later IS '1月后价格';
COMMENT ON COLUMN backtest_results.return_1d IS '1天收益率';
COMMENT ON COLUMN backtest_results.return_1w IS '1周收益率';
COMMENT ON COLUMN backtest_results.return_1m IS '1月收益率';
COMMENT ON COLUMN backtest_results.prediction_correct IS '预测是否正确（1/0）';
COMMENT ON COLUMN backtest_results.calculated_at IS '回测计算时间';
COMMENT ON COLUMN backtest_results.hold_days IS '持有天数（用于按持有期回测）';
COMMENT ON COLUMN backtest_results.return_at_hold IS '持有期收益率';


-- 索引（recommendations.db）
CREATE INDEX IF NOT EXISTS idx_stock_analysis_date
    ON stock_analysis(date);

CREATE INDEX IF NOT EXISTS idx_stock_analysis_symbol
    ON stock_analysis(symbol);

CREATE INDEX IF NOT EXISTS idx_agent_reports_date_symbol
    ON agent_reports(date, symbol);

CREATE INDEX IF NOT EXISTS idx_debate_history_date_symbol
    ON debate_history(date, symbol);

CREATE INDEX IF NOT EXISTS idx_pipeline_steps_date_symbol
    ON pipeline_steps(date, symbol);

CREATE INDEX IF NOT EXISTS idx_data_source_logs_date_symbol
    ON data_source_logs(date, symbol);

CREATE INDEX IF NOT EXISTS idx_backtest_results_date
    ON backtest_results(date);


-- =========================
-- B) 组合持久化相关表（portfolio.db）
-- =========================

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    timestamp TEXT NOT NULL,
    cash TEXT NOT NULL,
    initial_capital TEXT NOT NULL,
    commission_rate TEXT NOT NULL,
    total_value TEXT,
    metadata TEXT
);

COMMENT ON TABLE portfolio_snapshots IS '组合快照主表';
COMMENT ON COLUMN portfolio_snapshots.id IS '主键ID';
COMMENT ON COLUMN portfolio_snapshots.timestamp IS '快照时间';
COMMENT ON COLUMN portfolio_snapshots.cash IS '现金余额（字符串形式）';
COMMENT ON COLUMN portfolio_snapshots.initial_capital IS '初始资金（字符串形式）';
COMMENT ON COLUMN portfolio_snapshots.commission_rate IS '手续费率（字符串形式）';
COMMENT ON COLUMN portfolio_snapshots.total_value IS '组合总市值（字符串形式）';
COMMENT ON COLUMN portfolio_snapshots.metadata IS '扩展元数据（通常为JSON字符串）';


CREATE TABLE IF NOT EXISTS positions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    snapshot_id BIGINT NOT NULL,
    ticker TEXT NOT NULL,
    quantity TEXT NOT NULL,
    cost_basis TEXT NOT NULL,
    sector TEXT,
    opened_at TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    stop_loss TEXT,
    take_profit TEXT,
    metadata TEXT,
    CONSTRAINT fk_positions_snapshot
        FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots(id)
);

COMMENT ON TABLE positions IS '持仓明细表';
COMMENT ON COLUMN positions.id IS '主键ID';
COMMENT ON COLUMN positions.snapshot_id IS '关联快照ID';
COMMENT ON COLUMN positions.ticker IS '股票代码';
COMMENT ON COLUMN positions.quantity IS '持仓数量（字符串形式）';
COMMENT ON COLUMN positions.cost_basis IS '成本价（字符串形式）';
COMMENT ON COLUMN positions.sector IS '行业';
COMMENT ON COLUMN positions.opened_at IS '建仓时间';
COMMENT ON COLUMN positions.last_updated IS '最近更新时间';
COMMENT ON COLUMN positions.stop_loss IS '止损价（字符串形式）';
COMMENT ON COLUMN positions.take_profit IS '止盈价（字符串形式）';
COMMENT ON COLUMN positions.metadata IS '扩展元数据（通常为JSON字符串）';


CREATE TABLE IF NOT EXISTS trades (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    snapshot_id BIGINT NOT NULL,
    ticker TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    exit_date TEXT,
    entry_price TEXT NOT NULL,
    exit_price TEXT,
    quantity TEXT NOT NULL,
    pnl TEXT,
    pnl_percent TEXT,
    commission TEXT NOT NULL,
    holding_period INTEGER,
    is_win INTEGER,
    CONSTRAINT fk_trades_snapshot
        FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots(id)
);

COMMENT ON TABLE trades IS '交易历史表';
COMMENT ON COLUMN trades.id IS '主键ID';
COMMENT ON COLUMN trades.snapshot_id IS '关联快照ID';
COMMENT ON COLUMN trades.ticker IS '股票代码';
COMMENT ON COLUMN trades.entry_date IS '开仓日期';
COMMENT ON COLUMN trades.exit_date IS '平仓日期';
COMMENT ON COLUMN trades.entry_price IS '开仓价（字符串形式）';
COMMENT ON COLUMN trades.exit_price IS '平仓价（字符串形式）';
COMMENT ON COLUMN trades.quantity IS '成交数量（字符串形式）';
COMMENT ON COLUMN trades.pnl IS '盈亏金额（字符串形式）';
COMMENT ON COLUMN trades.pnl_percent IS '盈亏百分比（字符串形式）';
COMMENT ON COLUMN trades.commission IS '手续费（字符串形式）';
COMMENT ON COLUMN trades.holding_period IS '持有时长（天）';
COMMENT ON COLUMN trades.is_win IS '是否盈利（1盈利，0亏损）';


-- 索引（portfolio.db）
CREATE INDEX IF NOT EXISTS idx_positions_snapshot
    ON positions(snapshot_id);

CREATE INDEX IF NOT EXISTS idx_trades_snapshot
    ON trades(snapshot_id);

CREATE INDEX IF NOT EXISTS idx_trades_ticker
    ON trades(ticker);
```

---

## 3. 数据库创建与初始化脚本

> 本节提供从空 PostgreSQL 实例到应用可运行的最小可执行脚本。
> 应用侧以 `frontend/backend/database.py` 中的 `init_db()` 为准进行建表、补列和索引初始化。

### 3.1 创建用户与数据库（可选，需管理员权限）

```sql
-- 1) 创建业务用户（若已存在可跳过）
CREATE USER tradingagents_app WITH PASSWORD 'change_me';

-- 2) 创建数据库并指定 owner（若已存在可跳过）
CREATE DATABASE tradingagents OWNER tradingagents_app;
```

### 3.2 授权（在目标数据库中执行）

```sql
-- 连接到目标库后执行
GRANT CONNECT ON DATABASE tradingagents TO tradingagents_app;
GRANT USAGE ON SCHEMA public TO tradingagents_app;
GRANT CREATE ON SCHEMA public TO tradingagents_app;

-- 兼容后续手工建表/迁移场景
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO tradingagents_app;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO tradingagents_app;
```

### 3.3 应用侧环境变量配置（`.env`）

优先方式（推荐）：

```dotenv
DATABASE_URL=postgresql://tradingagents_app:change_me@localhost:5432/tradingagents?sslmode=prefer
```

回退方式（仅当未设置 `DATABASE_URL` 时生效）：

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tradingagents
DB_USER=tradingagents_app
DB_PASSWORD=change_me
DB_SSLMODE=prefer
```

### 3.4 执行建表与索引初始化

应用启动时会显式调用 `db.init_db()` 完成：

- 7 张业务表创建（`daily_recommendations`、`stock_analysis`、`agent_reports`、`debate_history`、`pipeline_steps`、`data_source_logs`、`backtest_results`）
- 索引创建
- 幂等补列迁移（`ADD COLUMN` 路径）

也可在 Python 中单独执行一次初始化：

```python
import sys
from pathlib import Path

backend = Path("frontend/backend").resolve()
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend))

import database as db

db.init_db()
```

### 3.5 启动前校验步骤

```sql
-- 1) 检查表是否齐全
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN (
    'daily_recommendations',
    'stock_analysis',
    'agent_reports',
    'debate_history',
    'pipeline_steps',
    'data_source_logs',
    'backtest_results'
  )
ORDER BY tablename;

-- 2) 检查关键索引
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexname IN (
    'idx_stock_analysis_date',
    'idx_stock_analysis_symbol',
    'idx_agent_reports_date_symbol',
    'idx_debate_history_date_symbol',
    'idx_pipeline_steps_date_symbol',
    'idx_data_source_logs_date_symbol',
    'idx_backtest_results_date'
  )
ORDER BY indexname;
```

---

## 4. 迁移注意事项（建议）

1. **主键自增**：SQLite `AUTOINCREMENT` 已改为 PG `GENERATED ALWAYS AS IDENTITY`。
2. **时间字段**：当前为兼容保留 `TEXT`，建议后续按业务升级：
   - `date` -> `DATE`
   - `created_at / timestamp / started_at / completed_at` -> `TIMESTAMPTZ`
3. **数值字段**：组合相关大量金额字段当前是 `TEXT`（为保留 Decimal 原样字符串）；若后续要做 SQL 聚合分析，建议改成 `NUMERIC(20,8)`。
4. **布尔字段**：`success`、`is_win`、`prediction_correct` 可在后续迁移为 `BOOLEAN`。
5. **JSON 字段**：`top_picks`、`stocks_to_avoid`、`metadata`、`args` 等可逐步改成 `JSONB` 并加 GIN 索引。

---

## 5. 来源映射（便于追溯）

- `frontend/backend/database.py`：定义了推荐分析相关 7 张表、迁移列（`hold_days`、`rank`、`return_at_hold` 等）和索引。
- `tradingagents/portfolio/persistence.py`：定义了组合相关 3 张表及 3 个索引。

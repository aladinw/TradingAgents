export type Decision = 'BUY' | 'SELL' | 'HOLD';
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW';
export type Risk = 'HIGH' | 'MEDIUM' | 'LOW';

export interface ReturnBreakdown {
  correctPredictions: {
    count: number;
    totalReturn: number;
    avgReturn: number;
    stocks: { symbol: string; decision: string; return1d: number }[];
  };
  incorrectPredictions: {
    count: number;
    totalReturn: number;
    avgReturn: number;
    stocks: { symbol: string; decision: string; return1d: number }[];
  };
  weightedReturn: number;
  formula: string;
}

// Backtest Types
export interface PricePoint {
  date: string;
  price: number;
}

export interface BacktestResult {
  prediction_correct: boolean;
  actual_return_1d: number;   // next trading day percentage return
  actual_return_1w: number;   // percentage
  actual_return_1m: number;   // percentage
  price_at_prediction: number;
  current_price: number;
  price_history: PricePoint[];
}

export interface AccuracyMetrics {
  total_predictions: number;
  correct_predictions: number;
  success_rate: number;
  buy_accuracy: number;
  sell_accuracy: number;
  hold_accuracy: number;
}

// Date-level statistics for history page
export interface DateStats {
  date: string;
  avgReturn1d: number;        // Average next-day return for all stocks
  avgReturn1m: number;        // Average 1-month return
  totalStocks: number;
  correctPredictions: number;
  accuracy: number;
  buyCount: number;
  sellCount: number;
  holdCount: number;
}

export interface OverallStats {
  totalDays: number;
  totalPredictions: number;
  avgDailyReturn: number;
  avgMonthlyReturn: number;
  overallAccuracy: number;
  bestDay: { date: string; return: number } | null;
  worstDay: { date: string; return: number } | null;
}

export interface StockAnalysis {
  symbol: string;
  company_name: string;
  decision: Decision | null;
  confidence?: Confidence;
  risk?: Risk;
  raw_analysis?: string;
  hold_days?: number | null;
  rank?: number | null;
  error?: string | null;
}

export interface RankingResult {
  ranking: string;
  stocks_analyzed: number;
  timestamp: string;
  error?: string;
}

export interface TopPick {
  rank: number;
  symbol: string;
  company_name: string;
  decision: string;
  reason: string;
  risk_level: Risk;
}

export interface StockToAvoid {
  symbol: string;
  company_name: string;
  reason: string;
}

export interface DailyRecommendation {
  date: string;
  analysis: Record<string, StockAnalysis>;
  ranking?: RankingResult;  // Optional since API may not return it
  summary: {
    total: number;
    buy: number;
    sell: number;
    hold: number;
  };
  top_picks: TopPick[];
  stocks_to_avoid: StockToAvoid[];
}

export interface HistoricalEntry {
  date: string;
  symbol: string;
  company_name: string;
  decision: Decision;
  confidence?: Confidence;
  risk?: Risk;
  hold_days?: number | null;
  rank?: number | null;
}

export interface StockHistory {
  symbol: string;
  company_name: string;
  history: HistoricalEntry[];
  stats: {
    total_recommendations: number;
    buy_count: number;
    sell_count: number;
    hold_count: number;
    accuracy?: number;
  };
}

export interface SP500Stock {
  symbol: string;
  company_name: string;
  sector?: string;
}

// S&P 500 Index data point
export interface SP500IndexPoint {
  date: string;
  value: number;
  return: number; // daily return %
}

// Risk metrics for portfolio analysis
export interface RiskMetrics {
  sharpeRatio: number;      // (mean return - risk-free) / std dev
  maxDrawdown: number;      // peak-to-trough decline %
  winLossRatio: number;     // avg win / avg loss
  winRate: number;          // % of winning predictions
  volatility: number;       // std dev of returns
  totalTrades: number;
  // Additional calculation details for showing formulas
  meanReturn?: number;
  riskFreeRate?: number;
  winningTrades?: number;
  losingTrades?: number;
  avgWinReturn?: number;
  avgLossReturn?: number;
  peakValue?: number;
  troughValue?: number;
}

// Return distribution bucket
export interface ReturnBucket {
  range: string;       // e.g., "0% to 1%"
  min: number;
  max: number;
  count: number;
  stocks: string[];    // symbols in this bucket
}

// Filter state for History page
export interface FilterState {
  decision: 'ALL' | 'BUY' | 'SELL' | 'HOLD';
  confidence: 'ALL' | 'HIGH' | 'MEDIUM' | 'LOW';
  sector: string;
  sortBy: 'symbol' | 'return' | 'accuracy';
  sortOrder: 'asc' | 'desc';
}

// Accuracy trend data point
export interface AccuracyTrendPoint {
  date: string;
  overall: number;
  buy: number;
  sell: number;
  hold: number;
}

// Cumulative return data point for index comparison chart
export interface CumulativeReturnPoint {
  date: string;
  value: number;
  aiReturn: number;
  indexReturn: number;
}

export const SP500_TOP_50_STOCKS: SP500Stock[] = [
  { symbol: 'AAPL', company_name: 'Apple Inc.', sector: 'Technology' },
  { symbol: 'MSFT', company_name: 'Microsoft Corporation', sector: 'Technology' },
  { symbol: 'NVDA', company_name: 'NVIDIA Corporation', sector: 'Technology' },
  { symbol: 'AMZN', company_name: 'Amazon.com, Inc.', sector: 'Consumer Discretionary' },
  { symbol: 'GOOGL', company_name: 'Alphabet Inc.', sector: 'Communication Services' },
  { symbol: 'META', company_name: 'Meta Platforms, Inc.', sector: 'Communication Services' },
  { symbol: 'BRK-B', company_name: 'Berkshire Hathaway Inc.', sector: 'Financials' },
  { symbol: 'AVGO', company_name: 'Broadcom Inc.', sector: 'Technology' },
  { symbol: 'LLY', company_name: 'Eli Lilly and Company', sector: 'Healthcare' },
  { symbol: 'JPM', company_name: 'JPMorgan Chase & Co.', sector: 'Financials' },
  { symbol: 'TSLA', company_name: 'Tesla, Inc.', sector: 'Consumer Discretionary' },
  { symbol: 'XOM', company_name: 'Exxon Mobil Corporation', sector: 'Energy' },
  { symbol: 'UNH', company_name: 'UnitedHealth Group Incorporated', sector: 'Healthcare' },
  { symbol: 'V', company_name: 'Visa Inc.', sector: 'Financials' },
  { symbol: 'MA', company_name: 'Mastercard Incorporated', sector: 'Financials' },
  { symbol: 'PG', company_name: 'The Procter & Gamble Company', sector: 'Consumer Staples' },
  { symbol: 'COST', company_name: 'Costco Wholesale Corporation', sector: 'Consumer Staples' },
  { symbol: 'JNJ', company_name: 'Johnson & Johnson', sector: 'Healthcare' },
  { symbol: 'HD', company_name: 'The Home Depot, Inc.', sector: 'Consumer Discretionary' },
  { symbol: 'ABBV', company_name: 'AbbVie Inc.', sector: 'Healthcare' },
  { symbol: 'WMT', company_name: 'Walmart Inc.', sector: 'Consumer Staples' },
  { symbol: 'NFLX', company_name: 'Netflix, Inc.', sector: 'Communication Services' },
  { symbol: 'CRM', company_name: 'Salesforce, Inc.', sector: 'Technology' },
  { symbol: 'BAC', company_name: 'Bank of America Corporation', sector: 'Financials' },
  { symbol: 'ORCL', company_name: 'Oracle Corporation', sector: 'Technology' },
  { symbol: 'CVX', company_name: 'Chevron Corporation', sector: 'Energy' },
  { symbol: 'MRK', company_name: 'Merck & Co., Inc.', sector: 'Healthcare' },
  { symbol: 'KO', company_name: 'The Coca-Cola Company', sector: 'Consumer Staples' },
  { symbol: 'AMD', company_name: 'Advanced Micro Devices, Inc.', sector: 'Technology' },
  { symbol: 'CSCO', company_name: 'Cisco Systems, Inc.', sector: 'Technology' },
  { symbol: 'PEP', company_name: 'PepsiCo, Inc.', sector: 'Consumer Staples' },
  { symbol: 'ACN', company_name: 'Accenture plc', sector: 'Technology' },
  { symbol: 'TMO', company_name: 'Thermo Fisher Scientific Inc.', sector: 'Healthcare' },
  { symbol: 'LIN', company_name: 'Linde plc', sector: 'Materials' },
  { symbol: 'ADBE', company_name: 'Adobe Inc.', sector: 'Technology' },
  { symbol: 'MCD', company_name: "McDonald's Corporation", sector: 'Consumer Discretionary' },
  { symbol: 'ABT', company_name: 'Abbott Laboratories', sector: 'Healthcare' },
  { symbol: 'WFC', company_name: 'Wells Fargo & Company', sector: 'Financials' },
  { symbol: 'GE', company_name: 'GE Aerospace', sector: 'Industrials' },
  { symbol: 'IBM', company_name: 'International Business Machines Corporation', sector: 'Technology' },
  { symbol: 'DHR', company_name: 'Danaher Corporation', sector: 'Healthcare' },
  { symbol: 'QCOM', company_name: 'QUALCOMM Incorporated', sector: 'Technology' },
  { symbol: 'CAT', company_name: 'Caterpillar Inc.', sector: 'Industrials' },
  { symbol: 'INTU', company_name: 'Intuit Inc.', sector: 'Technology' },
  { symbol: 'DIS', company_name: 'The Walt Disney Company', sector: 'Communication Services' },
  { symbol: 'AMAT', company_name: 'Applied Materials, Inc.', sector: 'Technology' },
  { symbol: 'TXN', company_name: 'Texas Instruments Incorporated', sector: 'Technology' },
  { symbol: 'NOW', company_name: 'ServiceNow, Inc.', sector: 'Technology' },
  { symbol: 'PM', company_name: 'Philip Morris International Inc.', sector: 'Consumer Staples' },
  { symbol: 'GS', company_name: 'The Goldman Sachs Group, Inc.', sector: 'Financials' },
];

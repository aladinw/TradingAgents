/**
 * US Stock Trading Cost Calculator
 *
 * Implements US equity trading cost estimation.
 * Most major US brokers (Schwab, Fidelity, etc.) offer commission-free trading.
 * Regulatory fees (SEC Fee, TAF Fee) still apply but are minimal.
 */

export interface BrokerageBreakdown {
  brokerage: number;
  secFee: number;
  tafFee: number;
  totalCharges: number;
  netProfit: number;
  turnover: number;
}

export interface TradeDetails {
  buyPrice: number;
  sellPrice: number;
  quantity: number;
  tradeType: 'delivery' | 'intraday';
}

// US regulatory fee rates (as of 2024-2025)
const RATES = {
  // SEC Fee: charged on sell orders only
  // Rate: $8.00 per $1,000,000 of principal (sell side)
  secFeeRate: 0.000008, // $8 / $1,000,000
  // TAF (Trading Activity Fee): charged on sell orders only
  // Rate: $0.000166 per share (sell side), max $8.30 per trade
  tafPerShare: 0.000166,
  tafCap: 8.30,
};

/**
 * Calculate trading costs for a single trade
 */
export function calculateBrokerage(trade: TradeDetails): BrokerageBreakdown {
  const { buyPrice, sellPrice, quantity } = trade;
  const buyValue = buyPrice * quantity;
  const sellValue = sellPrice * quantity;
  const turnover = buyValue + sellValue;

  // Commission-free (most US brokers)
  const brokerage = 0;

  // SEC Fee on sell value only
  const secFee = Math.round(sellValue * RATES.secFeeRate * 100) / 100;

  // TAF Fee on sell shares only
  const tafFee = Math.min(
    Math.round(quantity * RATES.tafPerShare * 100) / 100,
    RATES.tafCap
  );

  const totalCharges = brokerage + secFee + tafFee;
  const netProfit = sellValue - buyValue - totalCharges;

  return {
    brokerage,
    secFee,
    tafFee,
    totalCharges,
    netProfit,
    turnover,
  };
}

/**
 * Calculate total costs for multiple trades
 */
export function calculateTotalBrokerage(
  trades: TradeDetails[]
): {
  breakdown: BrokerageBreakdown;
  tradeCount: number;
} {
  const totals: BrokerageBreakdown = {
    brokerage: 0,
    secFee: 0,
    tafFee: 0,
    totalCharges: 0,
    netProfit: 0,
    turnover: 0,
  };

  for (const trade of trades) {
    const result = calculateBrokerage(trade);
    totals.brokerage += result.brokerage;
    totals.secFee += result.secFee;
    totals.tafFee += result.tafFee;
    totals.totalCharges += result.totalCharges;
    totals.netProfit += result.netProfit;
    totals.turnover += result.turnover;
  }

  return {
    breakdown: totals,
    tradeCount: trades.length,
  };
}

/**
 * Quick estimate for a round-trip delivery trade
 */
export function estimateDeliveryCharges(
  buyPrice: number,
  sellPrice: number,
  quantity: number
): BrokerageBreakdown {
  return calculateBrokerage({
    buyPrice,
    sellPrice,
    quantity,
    tradeType: 'delivery',
  });
}

/**
 * Quick estimate for intraday trade
 */
export function estimateIntradayCharges(
  buyPrice: number,
  sellPrice: number,
  quantity: number
): BrokerageBreakdown {
  return calculateBrokerage({
    buyPrice,
    sellPrice,
    quantity,
    tradeType: 'intraday',
  });
}

/**
 * Format currency in USD
 */
export function formatUSD(value: number, decimals: number = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

// Asset types
export interface Asset {
  symbol: string;
  base_currency: string;
  price: number;
  delta_24h: number;
  zf_score: number;
  psi_total: number;
  d_res: number;
  oi: number;
  funding_rate: number;
  volume_24h: number;
  bid_depth_ratio: number;
  ofi: number;
  mode: "heartbeat" | "deep_analysis";
  status: "normal" | "waspada" | "code_red";
  predicted_change_pct: number;
  cluster_id: number | null;
}

export interface AssetDetail extends Asset {
  history?: AssetSnapshot[];
}

export interface AssetSnapshot {
  time: string;
  symbol: string;
  price: number;
  zf_score: number;
  psi_total: number;
  d_res: number;
  oi: number;
  funding_rate: number | null;
  volume_24h: number;
  mode: string;
  status: string;
  predicted_change_pct: number | null;
}

// Prediction types
export interface PredictionAsset {
  rank: number;
  symbol: string;
  price: number;
  zf_score: number;
  psi_total: number;
  d_res: number;
  predicted_change_pct: number;
}

export interface PredictionTop20 {
  title: string;
  market_direction: "up" | "down" | "neutral";
  assets: PredictionAsset[];
}

// User types
export interface User {
  id: number;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  role: "super_admin" | "architect";
  status: "active" | "suspended" | "banned";
  created_at: string;
  last_login: string | null;
}

// API Key types
export interface ApiKey {
  id: number;
  label: string | null;
  api_key_last4: string;
  permission_level: string | null;
  is_valid: boolean;
  created_at: string;
  last_tested_at: string | null;
}

// Demo types
export interface DemoWallet {
  id: number;
  user_id: number;
  balance: number;
  initial_balance: number;
  total_pnl: number;
  total_trades: number;
  win_trades: number;
  win_rate: number;
  unrealized_pnl: number;
  created_at: string;
  last_reset_at: string;
}

export interface DemoPosition {
  id: number;
  user_id: number;
  symbol: string;
  side: "long" | "short";
  size_usdt: number;
  leverage: number;
  entry_price: number;
  exit_price: number | null;
  margin: number;
  pnl: number | null;
  fee: number | null;
  status: "open" | "closed";
  close_reason: "manual" | "take_profit" | "stop_loss" | "liquidation" | null;
  opened_at: string;
  closed_at: string | null;
  // Client-side computed
  mark_price?: number;
  unrealized_pnl?: number;
}

// System types
export interface SystemStatus {
  circuit_breaker: boolean;
  cold_mode: boolean;
  assets_monitored: number;
  assets_deep_analysis: number;
  last_data_received: string;
}

// Session comparison
export interface SessionComparison {
  symbol: string;
  zf_score_prev: number;
  zf_score_curr: number;
  delta: number;
  transition: "worsening" | "improving" | "stable";
}

// OrderBook
export interface OrderBookData {
  bids: [number, number][]; // [price, volume]
  asks: [number, number][];
  bid_depth_ratio: number;
}

// WebSocket message wrapper
export interface WSMessage<T = unknown> {
  type: string;
  data: T;
}

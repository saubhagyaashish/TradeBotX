# Graph Report - TradeBotX  (2026-04-23)

## Corpus Check
- 88 files · ~287,876 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 776 nodes · 1536 edges · 18 communities detected
- Extraction: 60% EXTRACTED · 40% INFERRED · 0% AMBIGUOUS · INFERRED: 612 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]

## God Nodes (most connected - your core abstractions)
1. `UpstoxClient` - 86 edges
2. `TradingAgentsGraph` - 86 edges
3. `UpstoxConfig` - 74 edges
4. `PaperTrader` - 61 edges
5. `AnalystType` - 31 edges
6. `AgentState` - 30 edges
7. `BaseLLMClient` - 27 edges
8. `ConditionalLogic` - 25 edges
9. `StatsCallbackHandler` - 24 edges
10. `run_analysis()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `scheduler.py — Background pre-market scanner for TradeBotX.  Runs a full screene` --uses--> `TradingAgentsGraph`  [INFERRED]
  scheduler.py → tradingagents\graph\trading_graph.py
- `Load scheduler config from config.json, merged with defaults.` --uses--> `TradingAgentsGraph`  [INFERRED]
  scheduler.py → tradingagents\graph\trading_graph.py
- `Persist scheduler config back to config.json.` --uses--> `TradingAgentsGraph`  [INFERRED]
  scheduler.py → tradingagents\graph\trading_graph.py
- `Return a flat list of ticker strings based on config source.` --uses--> `TradingAgentsGraph`  [INFERRED]
  scheduler.py → tradingagents\graph\trading_graph.py
- `Execute the pre-market scan:       1. Load tickers from configured source.` --uses--> `TradingAgentsGraph`  [INFERRED]
  scheduler.py → tradingagents\graph\trading_graph.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (119): add_to_watchlist(), analyze_batch(), analyze_stock(), analyze_stream(), AnalyzeRequest, BatchAnalyzeRequest, _detect_phase(), _extract_rating() (+111 more)

### Community 1 - "Community 1"
Cohesion: 0.04
Nodes (59): AgentState, InvestDebateState, RiskDebateState, create_aggressive_debator(), create_bear_researcher(), create_bull_researcher(), ConditionalLogic, Initialize with configuration parameters. (+51 more)

### Community 2 - "Community 2"
Cohesion: 0.04
Nodes (75): display_announcements(), fetch_announcements(), Fetch announcements from endpoint. Returns dict with announcements and settings., Display announcements panel. Prompts for Enter if require_attention is True., BaseCallbackHandler, Enum, analyze(), classify_message_type() (+67 more)

### Community 3 - "Community 3"
Cohesion: 0.05
Nodes (44): ABC, AnthropicClient, NormalizedChatAnthropic, ChatAnthropic with normalized content output.      Claude models with extended, Client for Anthropic Claude models., Return configured ChatAnthropic instance., Validate model for Anthropic., BaseLLMClient (+36 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (54): AlphaVantageRateLimitError, _filter_csv_by_date_range(), format_datetime_for_api(), get_api_key(), _make_api_request(), Retrieve the API key for Alpha Vantage from environment variables., Convert various date formats to YYYYMMDDTHHMM format required by Alpha Vantage A, Exception raised when Alpha Vantage API rate limit is exceeded. (+46 more)

### Community 5 - "Community 5"
Cohesion: 0.08
Nodes (38): get_config(), initialize_config(), Update the configuration with custom values., Get the current configuration., Initialize the configuration with default values., set_config(), _clean_dataframe(), filter_financials_by_date() (+30 more)

### Community 6 - "Community 6"
Cohesion: 0.06
Nodes (21): paper_portfolio(), paper_sell(), Position, paper_trader.py — Paper trading engine for TradeBotX.  Simulates trades with rea, Create paper trading tables if they don't exist., Reset daily counters at the start of a new trading day., Returns True if daily loss limit has been breached., Returns True if max positions limit reached. (+13 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (37): get_scheduler_config(), update_scheduler_config(), _conn(), fetch_price(), get_predictions(), get_stats(), get_total_count(), init_db() (+29 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (15): Close the HTTP client., upstox_ws.py — Upstox WebSocket V3 market data feed manager.  Provides real-time, Gracefully disconnect the WebSocket., Attempt to reconnect after a disconnect., Subscribe to market data for instruments.          Args:             instrument_, Unsubscribe from market data for instruments., Change subscription mode for instruments., Main listener loop — receives and dispatches messages. (+7 more)

### Community 9 - "Community 9"
Cohesion: 0.14
Nodes (23): compute_atr(), compute_bollinger_bands(), compute_ema(), compute_macd(), compute_rsi(), compute_sma(), compute_stochastic(), compute_vwap() (+15 more)

### Community 10 - "Community 10"
Cohesion: 0.21
Nodes (8): Add financial situations and their corresponding advice.          Args:, Reflect on investment judge's decision and update memory., Reflect on portfolio manager's decision and update memory., Extract the current market situation from the state., Generate reflection for a component., Reflect on bull researcher's analysis and update memory., Reflect on bear researcher's analysis and update memory., Reflect on trader's decision and update memory.

### Community 11 - "Community 11"
Cohesion: 0.2
Nodes (11): _clean(), _fetch_single_stock(), _fetch_tv_indicators(), get_index_stocks(), Indian market index screener using yfinance.  Since the NSE India API blocks p, Fetch RSI and volume data from TradingView for a single NSE stock.     Returns, Fetch live market data for all stocks in an index.     Uses yfinance with paral, Fetch index stocks and flag 'interesting' ones for deep analysis.      Screeni (+3 more)

### Community 12 - "Community 12"
Cohesion: 0.2
Nodes (3): handleFilter(), handleUpdateOutcomes(), load()

### Community 13 - "Community 13"
Cohesion: 0.2
Nodes (7): exchange_code_for_token(), get_login_url(), upstox_auth.py — Upstox OAuth 2.0 token management.  Handles:   - Loading access, Generate the OAuth login URL for the user to authorize.     After login, Upstox, Exchange the authorization code for an access token.     This is Step 2 of the O, Validate the access token by hitting the user profile endpoint.     Updates conf, validate_token()

### Community 14 - "Community 14"
Cohesion: 0.2
Nodes (6): build_instrument_context(), create_msg_delete(), get_language_instruction(), Return a prompt instruction for the configured output language.      Returns e, Describe the exact instrument so agents preserve exchange-qualified tickers., TickerSymbolHandlingTests

### Community 24 - "Community 24"
Cohesion: 1.0
Nodes (1): Unrealized P&L (not useful without current price).

### Community 36 - "Community 36"
Cohesion: 1.0
Nodes (1): Return the configured LLM instance.

### Community 37 - "Community 37"
Cohesion: 1.0
Nodes (1): Validate that the model is supported by this client.

## Knowledge Gaps
- **131 isolated node(s):** `database.py — SQLite prediction tracking for TradeBotX.  Schema: predictions(id,`, `Create tables if they don't exist. Safe to call multiple times.`, `Return the latest market price for a ticker, or None on error.`, `Upsert a prediction row. Returns the row id.`, `Return predictions newest-first, optionally filtered by rating.` (+126 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 24`** (1 nodes): `Unrealized P&L (not useful without current price).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 36`** (1 nodes): `Return the configured LLM instance.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 37`** (1 nodes): `Validate that the model is supported by this client.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TradingAgentsGraph` connect `Community 0` to `Community 1`, `Community 10`, `Community 2`, `Community 7`?**
  _High betweenness centrality (0.399) - this node is a cross-community bridge._
- **Why does `UpstoxClient` connect `Community 0` to `Community 8`?**
  _High betweenness centrality (0.139) - this node is a cross-community bridge._
- **Why does `PaperTrader` connect `Community 0` to `Community 6`?**
  _High betweenness centrality (0.103) - this node is a cross-community bridge._
- **Are the 58 inferred relationships involving `UpstoxClient` (e.g. with `AnalyzeRequest` and `TickerBody`) actually correct?**
  _`UpstoxClient` has 58 INFERRED edges - model-reasoned connections that need verification._
- **Are the 77 inferred relationships involving `TradingAgentsGraph` (e.g. with `AnalyzeRequest` and `TickerBody`) actually correct?**
  _`TradingAgentsGraph` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Are the 71 inferred relationships involving `UpstoxConfig` (e.g. with `AnalyzeRequest` and `TickerBody`) actually correct?**
  _`UpstoxConfig` has 71 INFERRED edges - model-reasoned connections that need verification._
- **Are the 43 inferred relationships involving `PaperTrader` (e.g. with `AnalyzeRequest` and `TickerBody`) actually correct?**
  _`PaperTrader` has 43 INFERRED edges - model-reasoned connections that need verification._
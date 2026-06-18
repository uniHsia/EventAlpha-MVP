CREATE TABLE IF NOT EXISTS raw_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_id TEXT UNIQUE NOT NULL,
    title TEXT,
    source TEXT,
    source_type TEXT,
    publish_time TEXT,
    url TEXT,
    language TEXT,
    raw_text TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    raw_id TEXT,
    event_type TEXT,
    event_title TEXT,
    summary TEXT,
    entities_json TEXT,
    locations_json TEXT,
    event_time TEXT,
    status TEXT,
    affected_industries_json TEXT,
    affected_assets_hint_json TEXT,
    novelty_score REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verification_id TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    credibility_score REAL,
    verification_status TEXT,
    source_classification TEXT,
    content_contains_official_claim INTEGER,
    evidence_json TEXT,
    risk_flags_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    score_id TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    impact_score INTEGER,
    event_level TEXT,
    trigger_alert INTEGER,
    tracking_mode TEXT,
    score_breakdown_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS causal_chains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chain_id TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    logic_json TEXT,
    affected_assets_json TEXT,
    direction TEXT,
    time_horizon TEXT,
    confidence REAL,
    rationale TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS anti_spurious_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_id TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    chain_id TEXT NOT NULL,
    spurious_risk TEXT,
    issues_json TEXT,
    required_verifications_json TEXT,
    adjusted_confidence REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mapping_id TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    mapped_assets_json TEXT,
    watch_indicators_json TEXT,
    mapping_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS event_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    event_title TEXT,
    event_level TEXT,
    credibility_score REAL,
    one_sentence TEXT,
    what_happened TEXT,
    sources_json TEXT,
    causal_chain_summary_json TEXT,
    possible_impacts_json TEXT,
    risk_factors_json TEXT,
    verification_indicators_json TEXT,
    risk_disclaimer TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prediction_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id TEXT UNIQUE NOT NULL,
    event_id TEXT NOT NULL,
    event_title TEXT,
    event_type TEXT,
    publish_time TEXT,
    event_level TEXT,
    credibility_score REAL,
    impact_score INTEGER,
    causal_chain_ids_json TEXT,
    risk_flags_json TEXT,
    review_schedule_json TEXT,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predicted_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id TEXT NOT NULL,
    asset_name TEXT NOT NULL,
    asset_type TEXT,
    direction TEXT,
    time_window TEXT,
    asset_confidence REAL,
    chain_confidence REAL,
    anti_spurious_adjusted_confidence REAL,
    final_confidence REAL,
    confidence REAL,
    benchmark TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    prediction_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    horizon TEXT,
    due_at TEXT,
    status TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS review_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id TEXT UNIQUE NOT NULL,
    prediction_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    horizon TEXT,
    asset_name TEXT,
    predicted_direction TEXT,
    benchmark TEXT,
    actual_return REAL,
    benchmark_return REAL,
    excess_return REAL,
    is_directional_call INTEGER,
    direction_correct INTEGER,
    outperformed_benchmark INTEGER,
    direction_evaluation_json TEXT,
    asset_confidence REAL,
    final_confidence REAL,
    causal_validity TEXT,
    review_conclusion TEXT,
    error_type TEXT,
    risk_disclaimer TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prediction_review_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_id TEXT UNIQUE NOT NULL,
    prediction_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    horizon TEXT,
    total_assets INTEGER,
    reviewed_assets INTEGER,
    direction_correct_count INTEGER,
    outperform_count INTEGER,
    valid_causal_count INTEGER,
    invalid_causal_count INTEGER,
    watch_or_mixed_count INTEGER,
    average_excess_return REAL,
    conclusion_level TEXT,
    summary_text TEXT,
    error_types_json TEXT,
    rule_update_suggestions_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS causal_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT UNIQUE NOT NULL,
    event_type TEXT,
    rule TEXT,
    weight REAL,
    success_rate REAL,
    review_count INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rule_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    update_id TEXT UNIQUE NOT NULL,
    rule_id TEXT NOT NULL,
    prediction_id TEXT NOT NULL,
    review_id TEXT NOT NULL,
    summary_id TEXT,
    old_weight REAL,
    new_weight REAL,
    reason TEXT,
    update_action TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

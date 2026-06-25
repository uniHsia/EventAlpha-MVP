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
    source_run_id TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT UNIQUE NOT NULL,
    source_type TEXT,
    enabled INTEGER DEFAULT 1,
    region TEXT,
    language TEXT,
    credibility_base REAL,
    fetch_mode TEXT,
    notes TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_check_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    check_run_id TEXT UNIQUE NOT NULL,
    source_run_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    query TEXT,
    status TEXT,
    fetched_at TEXT,
    item_count INTEGER,
    error_text TEXT,
    raw_result_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_news_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_item_id TEXT UNIQUE NOT NULL,
    source_run_id TEXT NOT NULL,
    news_id TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    url TEXT,
    source TEXT,
    source_type TEXT,
    published_at TEXT,
    language TEXT,
    country TEXT,
    raw_text TEXT,
    tags_json TEXT,
    fetched_at TEXT,
    query TEXT,
    is_duplicate INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_run_id, news_id)
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
    history_validation_summary_json TEXT,
    source_evidence_json TEXT,
    verification_status TEXT,
    official_confirmation TEXT,
    staleness_flag TEXT,
    prediction_gate_status TEXT,
    prediction_gate_reason TEXT,
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

CREATE TABLE IF NOT EXISTS event_clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cluster_record_id TEXT UNIQUE NOT NULL,
    source_run_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    canonical_title TEXT,
    canonical_summary TEXT,
    source_count INTEGER,
    item_count INTEGER,
    unique_source_count INTEGER,
    mainstream_source_count INTEGER,
    first_seen_at TEXT,
    last_seen_at TEXT,
    dominant_keywords_json TEXT,
    candidate_event_type TEXT,
    cluster_type TEXT,
    independent_confirmation INTEGER DEFAULT 0,
    verification_status TEXT,
    confidence REAL,
    debug_reasons_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_run_id, cluster_id)
);

CREATE TABLE IF NOT EXISTS cluster_news_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_run_id TEXT NOT NULL,
    cluster_id TEXT NOT NULL,
    news_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_run_id, cluster_id, news_id)
);

CREATE TABLE IF NOT EXISTS credibility_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_record_id TEXT UNIQUE NOT NULL,
    source_run_id TEXT,
    cluster_id TEXT,
    event_id TEXT,
    evidence_key TEXT NOT NULL,
    source_name TEXT,
    evidence_type TEXT,
    claim_text TEXT,
    supporting_item_ids_json TEXT,
    supporting_sources_json TEXT,
    consistency_status TEXT,
    official_evidence_status TEXT,
    risk_flags_json TEXT,
    note_text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_credibility_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT UNIQUE NOT NULL,
    source_type TEXT,
    credibility_tier TEXT,
    historical_accuracy REAL,
    weight REAL,
    last_verified_at TEXT,
    notes TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

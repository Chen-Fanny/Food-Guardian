-- ==============================================================================
-- Food Guardian Database Schema (Planned / Initial Specification)
-- Target DBMS: SQLite 3
-- ==============================================================================

-- 1. Food Inventory Table
CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    purchase_date TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    date_label_type TEXT CHECK(date_label_type IN ('use_by', 'best_before', 'opened_on')),
    storage_location TEXT CHECK(storage_location IN ('refrigerator', 'freezer', 'pantry')),
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'consumed', 'wasted')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Food Waste & Consumption Log Table
CREATE TABLE IF NOT EXISTS consumption_waste_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    item_name TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    action_type TEXT NOT NULL CHECK(action_type IN ('consumed', 'wasted')),
    reason TEXT, -- e.g., 'expired', 'spoiled', 'over-prepared'
    log_date TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES inventory_items(id) ON DELETE SET NULL
);

-- 3. AI Agent Recipe Recommendation Cache Table (Optional / Planned)
CREATE TABLE IF NOT EXISTS recipe_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_title TEXT NOT NULL,
    matched_ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'staff', 'admin')),
    profile_image TEXT,
    department TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS resources (
    resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    location TEXT NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity >= 0),
    images TEXT,
    availability_rules TEXT,
    requires_approval INTEGER NOT NULL DEFAULT 0 CHECK (requires_approval IN (0, 1)),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (owner_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,
    requester_id INTEGER NOT NULL,
    start_datetime TEXT NOT NULL,
    end_datetime TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled', 'completed')),
    approval_notes TEXT,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    updated_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    CHECK (end_datetime > start_datetime),
    FOREIGN KEY (resource_id) REFERENCES resources (resource_id) ON DELETE CASCADE,
    FOREIGN KEY (requester_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TRIGGER IF NOT EXISTS bookings_updated_at
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    UPDATE bookings SET updated_at = CURRENT_TIMESTAMP WHERE booking_id = NEW.booking_id;
END;

CREATE TABLE IF NOT EXISTS threads (
    thread_id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_type TEXT NOT NULL CHECK (context_type IN ('resource', 'booking', 'general')),
    context_id INTEGER,
    created_by INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (created_by) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (thread_id) REFERENCES threads (thread_id) ON DELETE CASCADE,
    FOREIGN KEY (sender_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER NOT NULL,
    reviewer_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (resource_id) REFERENCES resources (resource_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users (user_id) ON DELETE CASCADE,
    UNIQUE (resource_id, reviewer_id)
);

CREATE TABLE IF NOT EXISTS admin_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_table TEXT,
    details TEXT,
    timestamp TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    FOREIGN KEY (admin_id) REFERENCES users (user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX IF NOT EXISTS idx_resources_owner ON resources (owner_id);
CREATE INDEX IF NOT EXISTS idx_resources_status ON resources (status);
CREATE INDEX IF NOT EXISTS idx_bookings_resource ON bookings (resource_id);
CREATE INDEX IF NOT EXISTS idx_bookings_requester ON bookings (requester_id);
CREATE INDEX IF NOT EXISTS idx_bookings_window ON bookings (start_datetime, end_datetime);
CREATE INDEX IF NOT EXISTS idx_reviews_resource ON reviews (resource_id);
CREATE INDEX IF NOT EXISTS idx_threads_context ON threads (context_type, context_id);
CREATE INDEX IF NOT EXISTS idx_messages_thread_timestamp ON messages (thread_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_sender_receiver ON messages (sender_id, receiver_id);


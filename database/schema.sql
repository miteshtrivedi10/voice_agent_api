-- SQL schema for voice agent API database tables

-- Table for user voice sessions
CREATE TABLE IF NOT EXISTS user_voice_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    room_name TEXT NOT NULL,
    duration INTEGER DEFAULT 0,
    start_time TEXT,
    end_time TEXT
);

-- Table for file details
CREATE TABLE IF NOT EXISTS file_details (
    user_id TEXT NOT NULL,
    file_id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    subject TEXT,
    file_size INTEGER,
    file_type TEXT,
    is_processed BOOLEAN DEFAULT FALSE,
    total_generated_qna INTEGER DEFAULT 0,
    upload_timestamp TEXT,
    processed_timestamp TEXT
);
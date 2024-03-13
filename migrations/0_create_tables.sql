CREATE TABLE migrations (
    id INTEGER PRIMARY KEY,
    name TEXT
);

CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    comment TEXT
);

CREATE TABLE bot_rooms (
    id INTEGER PRIMARY KEY,
    room_id TEXT
);

CREATE TABLE queue (
    id INTEGER PRIMARY KEY,
    path TEXT,
    event_id TEXT,
    room_id TEXT
);

CREATE TABLE rooms_to_remove (
    id INTEGER PRIMARY KEY,
    event_id TEXT,
    room_id TEXT
);

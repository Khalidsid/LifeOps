CREATE TYPE task_category AS ENUM (
    'PROFESSIONAL',
    'PERSONAL',
    'HEALTH',
    'SPIRITUAL',
    'ADMIN',
    'FINANCE'
);

CREATE TYPE task_state AS ENUM (
    'BACKLOG',
    'ACTIVE',
    'STALLED',
    'BLOCKED',
    'DORMANT',
    'DONE',
    'DROPPED'
);

CREATE TYPE task_priority AS ENUM (
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    category task_category NOT NULL,
    state task_state NOT NULL,
    priority task_priority NOT NULL,
    deadline TIMESTAMPTZ NULL,
    next_action TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

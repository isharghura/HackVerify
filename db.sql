CREATE TABLE users (
    id BIGINT PRIMARY KEY,
    access_token TEXT,
    linkedin_id TEXT,
    full_name TEXT,
    picture TEXT,
    email TEXT
);

CREATE TABLE rate_limits (
    id BIGINT PRIMARY KEY,
    client_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    endpoint TEXT NOT NULL
);

CREATE TABLE interested_organizers (
    id BIGINT PRIMARY KEY,
    linkedin_id TEXT NOT NULL,
    devpost TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,
    name TEXT NOT NULL,
    website TEXT NOT NULL
);

CREATE TABLE devpost_hackathons (
    devpost_link TEXT PRIMARY KEY NOT NULL,
    last_scraped_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    datesandtimes TEXT NOT NULL,
    project_links TEXT NOT NULL,
    github_links TEXT NOT NULL
);
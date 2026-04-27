create extension if not exists "pgcrypto";

create table seasons (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    year int not null,
    active bool not null default false,
    created_at timestamptz not null default now()
);

create table users (
    id uuid primary key default gen_random_uuid(),
    username text unique not null,
    password_hash text not null,
    is_admin bool not null default false,
    created_at timestamptz not null default now()
);

create table athletes (
    id uuid primary key default gen_random_uuid(),
    firstcycling_id int unique not null,
    full_name text not null,
    nationality text,
    team text,
    last_synced_at timestamptz
);

create table user_athletes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    athlete_id uuid not null references athletes(id) on delete cascade,
    season_id uuid not null references seasons(id) on delete cascade,
    unique (user_id, athlete_id, season_id)
);

create table races (
    id uuid primary key default gen_random_uuid(),
    firstcycling_race_id int not null,
    name text not null,
    year int not null,
    num_stages int,
    race_type text not null check (race_type in ('stage_race', 'one_day')),
    race_date date,
    synced_at timestamptz
);

create table race_results (
    id uuid primary key default gen_random_uuid(),
    race_id uuid not null references races(id) on delete cascade,
    athlete_id uuid not null references athletes(id) on delete cascade,
    position int not null,
    points int not null default 0,
    result_type text not null check (result_type in ('gc', 'stage')),
    stage_number int,
    created_at timestamptz not null default now()
);

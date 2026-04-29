alter table races add column season_id uuid references seasons(id) on delete set null;
create index races_season_id_idx on races (season_id);

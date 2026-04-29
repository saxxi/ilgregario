alter table seasons
  add column if not exists total_budget int not null default 500,
  add column if not exists min_runners  int not null default 9,
  add column if not exists max_runners  int not null default 30;

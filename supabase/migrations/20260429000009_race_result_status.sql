alter table race_results
  add column status race_status not null default 'ok',
  alter column position drop not null,
  alter column time type interval using time::interval;

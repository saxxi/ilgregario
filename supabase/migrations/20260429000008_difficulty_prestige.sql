alter table races
  add column difficulty            smallint check (difficulty between 1 and 5),
  add column prestige              smallint check (prestige  between 1 and 5),
  add column difficulty_updated_at timestamptz,
  add column prestige_updated_at   timestamptz;

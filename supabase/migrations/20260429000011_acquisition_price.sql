alter table user_athletes
  add column acquisition_price numeric(10,2) check (acquisition_price >= 0);

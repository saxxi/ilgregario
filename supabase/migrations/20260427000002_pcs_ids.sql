-- make legacy firstcycling ids optional
alter table athletes alter column firstcycling_id drop not null;
alter table races alter column firstcycling_race_id drop not null;

-- add procyclingstats slugs (unique where set; postgres allows multiple nulls)
alter table athletes add column pcs_slug text unique;
alter table races add column pcs_slug text unique;

create extension if not exists unaccent;

create or replace function _slugify(v text) returns text
  language sql immutable strict as $$
    select trim(both '-' from regexp_replace(lower(unaccent(v)), '[^a-z0-9]+', '-', 'g'))
$$;

alter table athletes add column slug text;

update athletes
  set slug = coalesce(
    nullif(trim(pcs_slug), ''),
    _slugify(full_name)
  );

alter table athletes alter column slug set not null;
alter table athletes add constraint athletes_slug_unique unique (slug);

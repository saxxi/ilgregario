alter table user_athletes
    add constraint user_athletes_athlete_season_unique unique (athlete_id, season_id);

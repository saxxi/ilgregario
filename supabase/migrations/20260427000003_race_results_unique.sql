-- stage_number 0 = not a stage result; real stage numbers start at 1
alter table race_results alter column stage_number set default 0;
update race_results set stage_number = 0 where stage_number is null;
alter table race_results alter column stage_number set not null;

alter table race_results
    add constraint race_results_unique
    unique (race_id, athlete_id, result_type, stage_number);

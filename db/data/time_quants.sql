create or replace function generate_quants()
returns VOID as $$
begin
FOR day_ IN 0..6 LOOP
        for hour_ in 0..23 LOOP
                INSERT INTO time_quants (id, hour, day)
                VALUES (day_*100+hour_, hour_, day_)
                ON CONFLICT DO NOTHING;
END LOOP;
END LOOP;
END;
$$ LANGUAGE plpgsql;

commit;

SELECT generate_quants();
begin;

CREATE TABLE cities (
    id                  INT PRIMARY KEY,
    country             VARCHAR(64),
    city                VARCHAR(64),
    timezone            VARCHAR(64) NOT NULL DEFAULT 'UTC'
);

CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username          VARCHAR(64),
    first_name        VARCHAR(64),
    last_name         VARCHAR(64),
    bio               VARCHAR(512) ,
    city_id			  INT REFERENCES cities(id) ON DELETE CASCADE,
    rating            SMALLINT NOT NULL DEFAULT 0,
    created_at        TIMESTAMP NOT NULL DEFAULT now(),
    updated_at        TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE user_photos (
     user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
     photo_type VARCHAR(10) UNIQUE NOT NULL, -- icon/preview/big_picture
     photo_url         VARCHAR(64), -- photo url from telegram
     photo_s3_key      VARCHAR(32) -- photo s3 in s3 bucket with would be
);

CREATE TABLE user_telegram (
   user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
   telegram_id      VARCHAR(100) UNIQUE NOT NULL,
   telegram_username VARCHAR(64) NOT NULL,
   PRIMARY KEY (telegram_id)
);

CREATE TABLE user_contacts (
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    value      VARCHAR(100) UNIQUE NOT NULL,
    contact_type VARCHAR(10) NOT NULL,
    PRIMARY KEY (user_id, contact_type)
);

CREATE TABLE categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL
);


CREATE TABLE goals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE user_goals (
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    goal_id    UUID REFERENCES goals(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, goal_id)
);

CREATE TABLE skills (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) UNIQUE NOT null,
    weight     SMALLINT NOT NULL DEFAULT 0,
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE user_skills (
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    skill_id    UUID REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, skill_id)
);

CREATE TABLE user_mentor_skills (
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    skill_id    UUID REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, skill_id)
);

CREATE TABLE user_mentee_skills (
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    skill_id    UUID REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, skill_id)
);

CREATE TABLE matches (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
    target_user_id   UUID REFERENCES users(id) ON DELETE CASCADE, 
    date_at          TIMESTAMP NOT NULL DEFAULT now(),
    status       	 VARCHAR(20),   -- UNCOMPLETED / SKIPPED/ COMPLETED
    UNIQUE (user_id, target_user_id, date_at)
);

CREATE TABLE user_quants (
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    quant_id            UUID REFERENCES time_quants(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, quant_id)
);

CREATE TABLE time_quants (
    id           SMALLINT PRIMARY KEY,
    hour 		 SMALLINT,
    day          SMALLINT
);

create or replace function generate_quants()
returns VOID as $$
begin
    FOR day_ IN 0..6 LOOP
        for hour_ in 0..23 LOOP
                INSERT INTO time_quants (id, hour, day)
                VALUES (day_*100+hour_, hour_, day_      )
                ON CONFLICT DO NOTHING ;
        END LOOP;
        END LOOP;
    END;
$$ LANGUAGE plpgsql;

commit;



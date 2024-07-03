CREATE USER state_user with password 'state_password';
CREATE DATABASE state_db OWNER state_user;
--grant all privileges on database state_db to state_user;

CREATE USER pool_user with password 'pool_password';
CREATE DATABASE pool_db OWNER pool_user;
--grant all privileges on database pool_db to state_user;

CREATE USER events_user with password 'events_password';
CREATE DATABASE events_db OWNER events_user;
--grant all privileges on database events_db to events_user;

CREATE USER hash_user with password 'hash_password';
CREATE DATABASE hash_db OWNER hash_user;
grant all privileges on database hash_db to hash_user;

CREATE USER bridge_user with password 'bridge_password';
CREATE DATABASE bridge_db OWNER bridge_user;
grant all privileges on database bridge_db to bridge_user;

CREATE USER explorer_user with password 'explorer_password';
CREATE DATABASE explorer_db OWNER explorer_user;
grant all privileges on database explorer_db to explorer_user;

CREATE USER aggregator_user with password 'aggregator_password';
CREATE DATABASE aggregator_db OWNER aggregator_user;
grant all privileges on database aggregator_db to aggregator_user;

CREATE USER sync_user with password 'sync_password';
CREATE DATABASE sync_db OWNER sync_user;
grant all privileges on database sync_db to sync_user;

\connect events_db;
CREATE TYPE public.level_t AS ENUM ('emerg','alert','crit','err','warning','notice','info','debug');
CREATE TABLE public."event" (
    id bigserial NOT NULL,
    received_at timestamptz NULL DEFAULT CURRENT_TIMESTAMP,
    ip_address inet NULL,
    "source" varchar(32) NOT NULL,
    component varchar(32) NULL,
    "level" public."level_t" NOT NULL,
    event_id varchar(32) NOT NULL,
    description text NULL,
    "data" bytea NULL,
    "json" jsonb NULL,
    CONSTRAINT event_pkey PRIMARY KEY (id)
);
ALTER TABLE public."event" OWNER TO events_user;

\connect hash_db;
CREATE SCHEMA state AUTHORIZATION hash_user;
CREATE TABLE state.nodes (hash BYTEA PRIMARY KEY, data BYTEA NOT NULL);
CREATE TABLE state.program (hash BYTEA PRIMARY KEY, data BYTEA NOT NULL);

-- ALTER DATABASE prover_db OWNER TO prover_user;
-- ALTER SCHEMA state OWNER TO prover_user;
-- ALTER SCHEMA public OWNER TO prover_user;
ALTER TABLE state.nodes OWNER TO hash_user;
ALTER TABLE state.program OWNER TO hash_user;
-- ALTER USER prover_user SET SEARCH_PATH=state;

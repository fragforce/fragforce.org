--
-- PostgreSQL database dump
--

-- Dumped from database version 15.2 (Ubuntu 15.2-1.pgdg20.04+1)
-- Dumped by pg_dump version 15.2 (Ubuntu 15.2-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP TRIGGER IF EXISTS tlog_insert_trigger ON org._trigger_log;
DROP TRIGGER IF EXISTS hc_user_status_trigger ON org."user";
DROP TRIGGER IF EXISTS hc_user_logtrigger ON org."user";
DROP TRIGGER IF EXISTS hc_fragforce_event__c_status_trigger ON org.fragforce_event__c;
DROP TRIGGER IF EXISTS hc_fragforce_event__c_logtrigger ON org.fragforce_event__c;
DROP TRIGGER IF EXISTS hc_event_participant__c_status_trigger ON org.event_participant__c;
DROP TRIGGER IF EXISTS hc_event_participant__c_logtrigger ON org.event_participant__c;
DROP TRIGGER IF EXISTS hc_el_history__c_status_trigger ON org.el_history__c;
DROP TRIGGER IF EXISTS hc_el_history__c_logtrigger ON org.el_history__c;
DROP TRIGGER IF EXISTS hc_contact_status_trigger ON org.contact;
DROP TRIGGER IF EXISTS hc_contact_logtrigger ON org.contact;
DROP TRIGGER IF EXISTS hc_account_status_trigger ON org.account;
DROP TRIGGER IF EXISTS hc_account_logtrigger ON org.account;
DROP INDEX IF EXISTS org.idx__sf_event_log_sfid;
DROP INDEX IF EXISTS org.idx__sf_event_log_comp_key;
DROP INDEX IF EXISTS org.hcu_idx_user_sfid;
DROP INDEX IF EXISTS org.hcu_idx_fragforce_event__c_sfid;
DROP INDEX IF EXISTS org.hcu_idx_event_participant__c_sfid;
DROP INDEX IF EXISTS org.hcu_idx_el_history__c_sfid;
DROP INDEX IF EXISTS org.hcu_idx_contact_sfid;
DROP INDEX IF EXISTS org.hcu_idx_contact_extra_life_id__c;
DROP INDEX IF EXISTS org.hcu_idx_account_sfid;
DROP INDEX IF EXISTS org.hc_idx_user_systemmodstamp;
DROP INDEX IF EXISTS org.hc_idx_fragforce_event__c_systemmodstamp;
DROP INDEX IF EXISTS org.hc_idx_fragforce_event__c_site__c;
DROP INDEX IF EXISTS org.hc_idx_fragforce_event__c_name;
DROP INDEX IF EXISTS org.hc_idx_fragforce_event__c_lastmodifieddate;
DROP INDEX IF EXISTS org.hc_idx_fragforce_event__c_event_start_date__c;
DROP INDEX IF EXISTS org.hc_idx_fragforce_event__c_event_end_date__c;
DROP INDEX IF EXISTS org.hc_idx_event_participant__c_systemmodstamp;
DROP INDEX IF EXISTS org.hc_idx_event_participant__c_lastmodifieddate;
DROP INDEX IF EXISTS org.hc_idx_el_history__c_systemmodstamp;
DROP INDEX IF EXISTS org.hc_idx_el_history__c_lastmodifieddate;
DROP INDEX IF EXISTS org.hc_idx_contact_systemmodstamp;
DROP INDEX IF EXISTS org.hc_idx_account_type;
DROP INDEX IF EXISTS org.hc_idx_account_systemmodstamp;
DROP INDEX IF EXISTS org.hc_idx_account_recordtypeid;
DROP INDEX IF EXISTS org.hc_idx_account_parentid;
DROP INDEX IF EXISTS org.hc_idx_account_ownerid;
DROP INDEX IF EXISTS org.hc_idx_account_name;
DROP INDEX IF EXISTS org.hc_idx_account_masterrecordid;
DROP INDEX IF EXISTS org.hc_idx_account_lastmodifieddate;
DROP INDEX IF EXISTS org.hc_idx_account_el_id__c;
DROP INDEX IF EXISTS org._trigger_log_idx_state_table_name;
DROP INDEX IF EXISTS org._trigger_log_idx_state_id;
DROP INDEX IF EXISTS org._trigger_log_idx_created_at;
DROP INDEX IF EXISTS org._trigger_log_archive_idx_state_table_name;
DROP INDEX IF EXISTS org._trigger_log_archive_idx_record_id;
DROP INDEX IF EXISTS org._trigger_log_archive_idx_created_at;
ALTER TABLE IF EXISTS ONLY org."user" DROP CONSTRAINT IF EXISTS user_pkey;
ALTER TABLE IF EXISTS ONLY org.fragforce_event__c DROP CONSTRAINT IF EXISTS fragforce_event__c_pkey;
ALTER TABLE IF EXISTS ONLY org.event_participant__c DROP CONSTRAINT IF EXISTS event_participant__c_pkey;
ALTER TABLE IF EXISTS ONLY org.el_history__c DROP CONSTRAINT IF EXISTS el_history__c_pkey;
ALTER TABLE IF EXISTS ONLY org.contact DROP CONSTRAINT IF EXISTS contact_pkey;
ALTER TABLE IF EXISTS ONLY org.account DROP CONSTRAINT IF EXISTS account_pkey;
ALTER TABLE IF EXISTS ONLY org._trigger_log DROP CONSTRAINT IF EXISTS _trigger_log_pkey;
ALTER TABLE IF EXISTS ONLY org._trigger_log_archive DROP CONSTRAINT IF EXISTS _trigger_log_archive_pkey;
ALTER TABLE IF EXISTS ONLY org._sf_event_log DROP CONSTRAINT IF EXISTS _sf_event_log_pkey;
ALTER TABLE IF EXISTS ONLY org._hcmeta DROP CONSTRAINT IF EXISTS _hcmeta_pkey;
ALTER TABLE IF EXISTS org."user" ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS org.fragforce_event__c ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS org.event_participant__c ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS org.el_history__c ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS org.contact ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS org.account ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS org._trigger_log ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS org._sf_event_log ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS org._hcmeta ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS org.user_id_seq;
DROP TABLE IF EXISTS org."user";
DROP SEQUENCE IF EXISTS org.fragforce_event__c_id_seq;
DROP TABLE IF EXISTS org.fragforce_event__c;
DROP SEQUENCE IF EXISTS org.event_participant__c_id_seq;
DROP TABLE IF EXISTS org.event_participant__c;
DROP SEQUENCE IF EXISTS org.el_history__c_id_seq;
DROP TABLE IF EXISTS org.el_history__c;
DROP SEQUENCE IF EXISTS org.contact_id_seq;
DROP TABLE IF EXISTS org.contact;
DROP SEQUENCE IF EXISTS org.account_id_seq;
DROP TABLE IF EXISTS org.account;
DROP SEQUENCE IF EXISTS org._trigger_log_id_seq;
DROP TABLE IF EXISTS org._trigger_log_archive;
DROP TABLE IF EXISTS org._trigger_log;
DROP SEQUENCE IF EXISTS org._sf_event_log_id_seq;
DROP TABLE IF EXISTS org._sf_event_log;
DROP SEQUENCE IF EXISTS org._hcmeta_id_seq;
DROP TABLE IF EXISTS org._hcmeta;
DROP FUNCTION IF EXISTS org.tlog_notify_trigger();
DROP FUNCTION IF EXISTS org.hc_user_status();
DROP FUNCTION IF EXISTS org.hc_user_logger();
DROP FUNCTION IF EXISTS org.hc_fragforce_event__c_status();
DROP FUNCTION IF EXISTS org.hc_fragforce_event__c_logger();
DROP FUNCTION IF EXISTS org.hc_event_participant__c_status();
DROP FUNCTION IF EXISTS org.hc_event_participant__c_logger();
DROP FUNCTION IF EXISTS org.hc_el_history__c_status();
DROP FUNCTION IF EXISTS org.hc_el_history__c_logger();
DROP FUNCTION IF EXISTS org.hc_contact_status();
DROP FUNCTION IF EXISTS org.hc_contact_logger();
DROP FUNCTION IF EXISTS org.hc_capture_update_from_row(source_row public.hstore, table_name character varying, columns_to_include text[]);
DROP FUNCTION IF EXISTS org.hc_capture_insert_from_row(source_row public.hstore, table_name character varying, excluded_cols text[]);
DROP FUNCTION IF EXISTS org.hc_account_status();
DROP FUNCTION IF EXISTS org.hc_account_logger();
DROP SCHEMA IF EXISTS org;
--
-- Name: org; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA org;


--
-- Name: hc_account_logger(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_account_logger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$

        DECLARE
            trigger_row "org"."_trigger_log";
            excluded_cols text[] = ARRAY['_hc_lastop', '_hc_err']::text[];

        BEGIN
            -- VERSION 4 --
            trigger_row = ROW();
            trigger_row.id = nextval('"org"."_trigger_log_id_seq"');
            trigger_row.action = TG_OP::text;
            trigger_row.table_name = TG_TABLE_NAME::text;
            trigger_row.txid = txid_current();
            trigger_row.created_at = clock_timestamp();
            trigger_row.state = 'READONLY';

            IF (TG_OP = 'DELETE') THEN
                trigger_row.record_id = OLD.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                
                END IF;
            ELSEIF (TG_OP = 'INSERT') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.values = hstore(NEW.*) - excluded_cols;
            ELSEIF (TG_OP = 'UPDATE') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                trigger_row.values = (hstore(NEW.*) - hstore(trigger_row.old)) - excluded_cols;
                
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                END IF;
            END IF;

            INSERT INTO "org"."_trigger_log" VALUES (trigger_row.*);

            RETURN NULL;
        END;
        $$;


--
-- Name: hc_account_status(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_account_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                    BEGIN
                      IF (get_xmlbinary() = 'base64') THEN  -- user op
                        NEW._hc_lastop = 'PENDING';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      ELSE  -- connect op
                        IF (TG_OP = 'UPDATE' AND NEW._hc_lastop IS NOT NULL AND NEW._hc_lastop != OLD._hc_lastop) THEN
                            RETURN NEW;
                        END IF;

                        NEW._hc_lastop = 'SYNCED';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      END IF;
                    END;
                 $$;


--
-- Name: hc_capture_insert_from_row(public.hstore, character varying, text[]); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_capture_insert_from_row(source_row public.hstore, table_name character varying, excluded_cols text[] DEFAULT ARRAY[]::text[]) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            excluded_cols_standard text[] = ARRAY['_hc_lastop', '_hc_err']::text[];
            retval int;

        BEGIN
            -- VERSION 1 --

            IF (source_row -> 'id') IS NULL THEN
                -- source_row is required to have an int id value
                RETURN NULL;
            END IF;

            excluded_cols_standard := array_remove(
                array_remove(excluded_cols, 'id'), 'sfid') || excluded_cols_standard;
            INSERT INTO "org"."_trigger_log" (
                action, table_name, txid, created_at, state, record_id, values)
            VALUES (
                'INSERT', table_name, txid_current(), clock_timestamp(), 'NEW',
                (source_row -> 'id')::int,
                source_row - excluded_cols_standard
            ) RETURNING id INTO retval;
            RETURN retval;
        END;
        $$;


--
-- Name: hc_capture_update_from_row(public.hstore, character varying, text[]); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_capture_update_from_row(source_row public.hstore, table_name character varying, columns_to_include text[] DEFAULT ARRAY[]::text[]) RETURNS integer
    LANGUAGE plpgsql
    AS $$
        DECLARE
            excluded_cols_standard text[] = ARRAY['_hc_lastop', '_hc_err']::text[];
            excluded_cols text[];
            retval int;

        BEGIN
            -- VERSION 1 --

            IF (source_row -> 'id') IS NULL THEN
                -- source_row is required to have an int id value
                RETURN NULL;
            END IF;

            IF array_length(columns_to_include, 1) <> 0 THEN
                excluded_cols := array(
                    select skeys(source_row)
                    except
                    select unnest(columns_to_include)
                );
            END IF;
            excluded_cols_standard := excluded_cols || excluded_cols_standard;
            INSERT INTO "org"."_trigger_log" (
                action, table_name, txid, created_at, state, record_id, sfid, values, old)
            VALUES (
                'UPDATE', table_name, txid_current(), clock_timestamp(), 'NEW',
                (source_row -> 'id')::int, source_row -> 'sfid',
                source_row - excluded_cols_standard, NULL
            ) RETURNING id INTO retval;
            RETURN retval;
        END;
        $$;


--
-- Name: hc_contact_logger(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_contact_logger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$

        DECLARE
            trigger_row "org"."_trigger_log";
            excluded_cols text[] = ARRAY['_hc_lastop', '_hc_err']::text[];

        BEGIN
            -- VERSION 4 --
            trigger_row = ROW();
            trigger_row.id = nextval('"org"."_trigger_log_id_seq"');
            trigger_row.action = TG_OP::text;
            trigger_row.table_name = TG_TABLE_NAME::text;
            trigger_row.txid = txid_current();
            trigger_row.created_at = clock_timestamp();
            trigger_row.state = 'READONLY';

            IF (TG_OP = 'DELETE') THEN
                trigger_row.record_id = OLD.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                
                END IF;
            ELSEIF (TG_OP = 'INSERT') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.values = hstore(NEW.*) - excluded_cols;
            ELSEIF (TG_OP = 'UPDATE') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                trigger_row.values = (hstore(NEW.*) - hstore(trigger_row.old)) - excluded_cols;
                
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                END IF;
            END IF;

            INSERT INTO "org"."_trigger_log" VALUES (trigger_row.*);

            RETURN NULL;
        END;
        $$;


--
-- Name: hc_contact_status(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_contact_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                    BEGIN
                      IF (get_xmlbinary() = 'base64') THEN  -- user op
                        NEW._hc_lastop = 'PENDING';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      ELSE  -- connect op
                        IF (TG_OP = 'UPDATE' AND NEW._hc_lastop IS NOT NULL AND NEW._hc_lastop != OLD._hc_lastop) THEN
                            RETURN NEW;
                        END IF;

                        NEW._hc_lastop = 'SYNCED';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      END IF;
                    END;
                 $$;


--
-- Name: hc_el_history__c_logger(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_el_history__c_logger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$

        DECLARE
            trigger_row "org"."_trigger_log";
            excluded_cols text[] = ARRAY['_hc_lastop', '_hc_err']::text[];

        BEGIN
            -- VERSION 4 --
            trigger_row = ROW();
            trigger_row.id = nextval('"org"."_trigger_log_id_seq"');
            trigger_row.action = TG_OP::text;
            trigger_row.table_name = TG_TABLE_NAME::text;
            trigger_row.txid = txid_current();
            trigger_row.created_at = clock_timestamp();
            trigger_row.state = 'READONLY';

            IF (TG_OP = 'DELETE') THEN
                trigger_row.record_id = OLD.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                
                END IF;
            ELSEIF (TG_OP = 'INSERT') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.values = hstore(NEW.*) - excluded_cols;
            ELSEIF (TG_OP = 'UPDATE') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                trigger_row.values = (hstore(NEW.*) - hstore(trigger_row.old)) - excluded_cols;
                
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                END IF;
            END IF;

            INSERT INTO "org"."_trigger_log" VALUES (trigger_row.*);

            RETURN NULL;
        END;
        $$;


--
-- Name: hc_el_history__c_status(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_el_history__c_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                    BEGIN
                      IF (get_xmlbinary() = 'base64') THEN  -- user op
                        NEW._hc_lastop = 'PENDING';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      ELSE  -- connect op
                        IF (TG_OP = 'UPDATE' AND NEW._hc_lastop IS NOT NULL AND NEW._hc_lastop != OLD._hc_lastop) THEN
                            RETURN NEW;
                        END IF;

                        NEW._hc_lastop = 'SYNCED';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      END IF;
                    END;
                 $$;


--
-- Name: hc_event_participant__c_logger(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_event_participant__c_logger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$

        DECLARE
            trigger_row "org"."_trigger_log";
            excluded_cols text[] = ARRAY['_hc_lastop', '_hc_err']::text[];

        BEGIN
            -- VERSION 4 --
            trigger_row = ROW();
            trigger_row.id = nextval('"org"."_trigger_log_id_seq"');
            trigger_row.action = TG_OP::text;
            trigger_row.table_name = TG_TABLE_NAME::text;
            trigger_row.txid = txid_current();
            trigger_row.created_at = clock_timestamp();
            trigger_row.state = 'READONLY';

            IF (TG_OP = 'DELETE') THEN
                trigger_row.record_id = OLD.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                
                END IF;
            ELSEIF (TG_OP = 'INSERT') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.values = hstore(NEW.*) - excluded_cols;
            ELSEIF (TG_OP = 'UPDATE') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                trigger_row.values = (hstore(NEW.*) - hstore(trigger_row.old)) - excluded_cols;
                
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                END IF;
            END IF;

            INSERT INTO "org"."_trigger_log" VALUES (trigger_row.*);

            RETURN NULL;
        END;
        $$;


--
-- Name: hc_event_participant__c_status(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_event_participant__c_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                    BEGIN
                      IF (get_xmlbinary() = 'base64') THEN  -- user op
                        NEW._hc_lastop = 'PENDING';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      ELSE  -- connect op
                        IF (TG_OP = 'UPDATE' AND NEW._hc_lastop IS NOT NULL AND NEW._hc_lastop != OLD._hc_lastop) THEN
                            RETURN NEW;
                        END IF;

                        NEW._hc_lastop = 'SYNCED';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      END IF;
                    END;
                 $$;


--
-- Name: hc_fragforce_event__c_logger(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_fragforce_event__c_logger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$

        DECLARE
            trigger_row "org"."_trigger_log";
            excluded_cols text[] = ARRAY['_hc_lastop', '_hc_err']::text[];

        BEGIN
            -- VERSION 4 --
            trigger_row = ROW();
            trigger_row.id = nextval('"org"."_trigger_log_id_seq"');
            trigger_row.action = TG_OP::text;
            trigger_row.table_name = TG_TABLE_NAME::text;
            trigger_row.txid = txid_current();
            trigger_row.created_at = clock_timestamp();
            trigger_row.state = 'READONLY';

            IF (TG_OP = 'DELETE') THEN
                trigger_row.record_id = OLD.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                
                END IF;
            ELSEIF (TG_OP = 'INSERT') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.values = hstore(NEW.*) - excluded_cols;
            ELSEIF (TG_OP = 'UPDATE') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                trigger_row.values = (hstore(NEW.*) - hstore(trigger_row.old)) - excluded_cols;
                
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                END IF;
            END IF;

            INSERT INTO "org"."_trigger_log" VALUES (trigger_row.*);

            RETURN NULL;
        END;
        $$;


--
-- Name: hc_fragforce_event__c_status(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_fragforce_event__c_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                    BEGIN
                      IF (get_xmlbinary() = 'base64') THEN  -- user op
                        NEW._hc_lastop = 'PENDING';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      ELSE  -- connect op
                        IF (TG_OP = 'UPDATE' AND NEW._hc_lastop IS NOT NULL AND NEW._hc_lastop != OLD._hc_lastop) THEN
                            RETURN NEW;
                        END IF;

                        NEW._hc_lastop = 'SYNCED';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      END IF;
                    END;
                 $$;


--
-- Name: hc_user_logger(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_user_logger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$

        DECLARE
            trigger_row "org"."_trigger_log";
            excluded_cols text[] = ARRAY['_hc_lastop', '_hc_err']::text[];

        BEGIN
            -- VERSION 4 --
            trigger_row = ROW();
            trigger_row.id = nextval('"org"."_trigger_log_id_seq"');
            trigger_row.action = TG_OP::text;
            trigger_row.table_name = TG_TABLE_NAME::text;
            trigger_row.txid = txid_current();
            trigger_row.created_at = clock_timestamp();
            trigger_row.state = 'READONLY';

            IF (TG_OP = 'DELETE') THEN
                trigger_row.record_id = OLD.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                
                END IF;
            ELSEIF (TG_OP = 'INSERT') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.values = hstore(NEW.*) - excluded_cols;
            ELSEIF (TG_OP = 'UPDATE') THEN
                trigger_row.record_id = NEW.id;
                trigger_row.old = hstore(OLD.*) - excluded_cols;
                trigger_row.values = (hstore(NEW.*) - hstore(trigger_row.old)) - excluded_cols;
                
                IF (OLD.sfid IS NOT NULL) THEN
                    trigger_row.sfid = OLD.sfid;
                END IF;
            END IF;

            INSERT INTO "org"."_trigger_log" VALUES (trigger_row.*);

            RETURN NULL;
        END;
        $$;


--
-- Name: hc_user_status(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.hc_user_status() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
                    BEGIN
                      IF (get_xmlbinary() = 'base64') THEN  -- user op
                        NEW._hc_lastop = 'PENDING';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      ELSE  -- connect op
                        IF (TG_OP = 'UPDATE' AND NEW._hc_lastop IS NOT NULL AND NEW._hc_lastop != OLD._hc_lastop) THEN
                            RETURN NEW;
                        END IF;

                        NEW._hc_lastop = 'SYNCED';
                        NEW._hc_err = NULL;
                        RETURN NEW;
                      END IF;
                    END;
                 $$;


--
-- Name: tlog_notify_trigger(); Type: FUNCTION; Schema: org; Owner: -
--

CREATE FUNCTION org.tlog_notify_trigger() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
            DECLARE
             BEGIN
               -- VERSION 1 --
               PERFORM pg_notify('org.hc_trigger_log', 'ping');
               RETURN new;
             END;
            $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: _hcmeta; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org._hcmeta (
    id integer NOT NULL,
    hcver integer,
    org_id character varying(50),
    details text
);


--
-- Name: _hcmeta_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org._hcmeta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: _hcmeta_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org._hcmeta_id_seq OWNED BY org._hcmeta.id;


--
-- Name: _sf_event_log; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org._sf_event_log (
    id integer NOT NULL,
    table_name character varying(128),
    action character varying(7),
    synced_at timestamp with time zone DEFAULT now(),
    sf_timestamp timestamp with time zone,
    sfid character varying(20),
    record text,
    processed boolean
);


--
-- Name: _sf_event_log_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org._sf_event_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: _sf_event_log_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org._sf_event_log_id_seq OWNED BY org._sf_event_log.id;


--
-- Name: _trigger_log; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org._trigger_log (
    id integer NOT NULL,
    txid bigint,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    processed_at timestamp with time zone,
    processed_tx bigint,
    state character varying(8),
    action character varying(7),
    table_name character varying(128),
    record_id integer,
    sfid character varying(18),
    old text,
    "values" text,
    sf_result integer,
    sf_message text
);


--
-- Name: _trigger_log_archive; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org._trigger_log_archive (
    id integer NOT NULL,
    txid bigint,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    processed_at timestamp with time zone,
    processed_tx bigint,
    state character varying(8),
    action character varying(7),
    table_name character varying(128),
    record_id integer,
    sfid character varying(18),
    old text,
    "values" text,
    sf_result integer,
    sf_message text
);


--
-- Name: _trigger_log_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org._trigger_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: _trigger_log_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org._trigger_log_id_seq OWNED BY org._trigger_log.id;


--
-- Name: account; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org.account (
    jigsaw character varying(20),
    shippinglongitude double precision,
    shippingstate character varying(80),
    youtubeid__c character varying(80),
    numberofemployees integer,
    parentid character varying(18),
    recordtypeid character varying(18),
    shippingpostalcode character varying(20),
    billingcity character varying(40),
    billinglatitude double precision,
    accountsource character varying(40),
    shippingcountry character varying(80),
    lastvieweddate timestamp without time zone,
    shippinggeocodeaccuracy character varying(40),
    last_el_update__c timestamp without time zone,
    name character varying(255),
    site_el_raised__c double precision,
    lastmodifieddate timestamp without time zone,
    phone character varying(40),
    masterrecordid character varying(18),
    ownerid character varying(18),
    isdeleted boolean,
    site_el_goal__c double precision,
    systemmodstamp timestamp without time zone,
    el_id__c character varying(80),
    lastmodifiedbyid character varying(18),
    shippingstreet character varying(255),
    lastactivitydate date,
    billingpostalcode character varying(20),
    billinglongitude double precision,
    twitchid__c character varying(80),
    twitterid__c character varying(80),
    createddate timestamp without time zone,
    billingstate character varying(80),
    supplies__c text,
    jigsawcompanyid character varying(20),
    shippingcity character varying(40),
    shippinglatitude double precision,
    createdbyid character varying(18),
    type character varying(40),
    website character varying(255),
    billingcountry character varying(80),
    description text,
    billinggeocodeaccuracy character varying(40),
    photourl character varying(255),
    lastreferenceddate timestamp without time zone,
    sicdesc character varying(80),
    industry character varying(40),
    billingstreet character varying(255),
    site_email__c character varying(80),
    sfid character varying(18),
    id integer NOT NULL,
    _hc_lastop character varying(32),
    _hc_err text,
    nerd_in_chief__c character varying(18),
    mayedit boolean,
    islocked boolean,
    loot_guard__c character varying(18),
    site_info__c text,
    currencyisocode character varying(3),
    billingstatecode character varying(10),
    billingcountrycode character varying(10),
    vice_nerd_in_chief__c character varying(18),
    shippingstatecode character varying(10),
    iscustomerportal boolean,
    shippingcountrycode character varying(10),
    records_enforcer__c character varying(18)
);


--
-- Name: account_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org.account_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: account_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org.account_id_seq OWNED BY org.account.id;


--
-- Name: contact; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org.contact (
    lastname character varying(80),
    accountid character varying(18),
    name character varying(121),
    masterrecordid character varying(18),
    ownerid character varying(18),
    isdeleted boolean,
    systemmodstamp timestamp without time zone,
    department character varying(80),
    extra_life_id__c character varying(20),
    createddate timestamp without time zone,
    fragforce_org_user__c character varying(18),
    title character varying(128),
    extra_life_user_name__c character varying(50),
    firstname character varying(40),
    sfid character varying(18),
    id integer NOT NULL,
    _hc_lastop character varying(32),
    _hc_err text,
    currencyisocode character varying(3),
    contact_type__c character varying(255),
    last_el_update__c timestamp without time zone,
    mayedit boolean,
    createdbyid character varying(18)
);


--
-- Name: contact_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org.contact_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contact_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org.contact_id_seq OWNED BY org.contact.id;


--
-- Name: el_history__c; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org.el_history__c (
    currencyisocode character varying(3),
    contact__c character varying(18),
    year__c character varying(255),
    name character varying(80),
    raised__c double precision,
    lastmodifieddate timestamp without time zone,
    ownerid character varying(18),
    mayedit boolean,
    isdeleted boolean,
    goal__c double precision,
    systemmodstamp timestamp without time zone,
    el_id__c character varying(7),
    lastmodifiedbyid character varying(18),
    islocked boolean,
    createddate timestamp without time zone,
    createdbyid character varying(18),
    site__c character varying(18),
    sfid character varying(18),
    id integer NOT NULL,
    _hc_lastop character varying(32),
    _hc_err text
);


--
-- Name: el_history__c_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org.el_history__c_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: el_history__c_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org.el_history__c_id_seq OWNED BY org.el_history__c.id;


--
-- Name: event_participant__c; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org.event_participant__c (
    contact__c character varying(18),
    email_contact__c boolean,
    accepted_film__c boolean,
    lastvieweddate timestamp without time zone,
    name character varying(80),
    lastmodifieddate timestamp without time zone,
    mayedit boolean,
    fragforce_event__c character varying(18),
    isdeleted boolean,
    systemmodstamp timestamp without time zone,
    accepted_nda__c boolean,
    lastmodifiedbyid character varying(18),
    status__c character varying(255),
    lastactivitydate date,
    islocked boolean,
    createddate timestamp without time zone,
    name__c character varying(120),
    createdbyid character varying(18),
    lastreferenceddate timestamp without time zone,
    sfid character varying(18),
    id integer NOT NULL,
    _hc_lastop character varying(32),
    _hc_err text
);


--
-- Name: event_participant__c_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org.event_participant__c_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_participant__c_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org.event_participant__c_id_seq OWNED BY org.event_participant__c.id;


--
-- Name: fragforce_event__c; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org.fragforce_event__c (
    lastvieweddate timestamp without time zone,
    volunteerforce_link__c character varying(255),
    name character varying(80),
    event_end_date__c timestamp without time zone,
    lastmodifieddate timestamp without time zone,
    isdeleted boolean,
    systemmodstamp timestamp without time zone,
    lastmodifiedbyid character varying(18),
    use_secondary_address__c boolean,
    lastactivitydate date,
    event_start_date__c timestamp without time zone,
    createddate timestamp without time zone,
    createdbyid character varying(18),
    stream_recording_link__c character varying(255),
    site__c character varying(18),
    lastreferenceddate timestamp without time zone,
    sfid character varying(18),
    id integer NOT NULL,
    _hc_lastop character varying(32),
    _hc_err text,
    mayedit boolean,
    islocked boolean,
    event_information__c text,
    description__c text,
    currencyisocode character varying(3)
);


--
-- Name: fragforce_event__c_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org.fragforce_event__c_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: fragforce_event__c_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org.fragforce_event__c_id_seq OWNED BY org.fragforce_event__c.id;


--
-- Name: user; Type: TABLE; Schema: org; Owner: -
--

CREATE TABLE org."user" (
    lastname character varying(80),
    usertype character varying(40),
    aboutme character varying(1000),
    accountid character varying(18),
    contactid__c character varying(18),
    name character varying(121),
    isactive boolean,
    systemmodstamp timestamp without time zone,
    alias character varying(8),
    createddate timestamp without time zone,
    title character varying(80),
    firstname character varying(40),
    contactid character varying(18),
    userroleid character varying(18),
    sfid character varying(18),
    id integer NOT NULL,
    _hc_lastop character varying(32),
    _hc_err text,
    companyname character varying(80)
);


--
-- Name: user_id_seq; Type: SEQUENCE; Schema: org; Owner: -
--

CREATE SEQUENCE org.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: org; Owner: -
--

ALTER SEQUENCE org.user_id_seq OWNED BY org."user".id;


--
-- Name: _hcmeta id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org._hcmeta ALTER COLUMN id SET DEFAULT nextval('org._hcmeta_id_seq'::regclass);


--
-- Name: _sf_event_log id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org._sf_event_log ALTER COLUMN id SET DEFAULT nextval('org._sf_event_log_id_seq'::regclass);


--
-- Name: _trigger_log id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org._trigger_log ALTER COLUMN id SET DEFAULT nextval('org._trigger_log_id_seq'::regclass);


--
-- Name: account id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.account ALTER COLUMN id SET DEFAULT nextval('org.account_id_seq'::regclass);


--
-- Name: contact id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.contact ALTER COLUMN id SET DEFAULT nextval('org.contact_id_seq'::regclass);


--
-- Name: el_history__c id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.el_history__c ALTER COLUMN id SET DEFAULT nextval('org.el_history__c_id_seq'::regclass);


--
-- Name: event_participant__c id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.event_participant__c ALTER COLUMN id SET DEFAULT nextval('org.event_participant__c_id_seq'::regclass);


--
-- Name: fragforce_event__c id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.fragforce_event__c ALTER COLUMN id SET DEFAULT nextval('org.fragforce_event__c_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: org; Owner: -
--

ALTER TABLE ONLY org."user" ALTER COLUMN id SET DEFAULT nextval('org.user_id_seq'::regclass);


--
-- Name: _hcmeta _hcmeta_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org._hcmeta
    ADD CONSTRAINT _hcmeta_pkey PRIMARY KEY (id);


--
-- Name: _sf_event_log _sf_event_log_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org._sf_event_log
    ADD CONSTRAINT _sf_event_log_pkey PRIMARY KEY (id);


--
-- Name: _trigger_log_archive _trigger_log_archive_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org._trigger_log_archive
    ADD CONSTRAINT _trigger_log_archive_pkey PRIMARY KEY (id);


--
-- Name: _trigger_log _trigger_log_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org._trigger_log
    ADD CONSTRAINT _trigger_log_pkey PRIMARY KEY (id);


--
-- Name: account account_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.account
    ADD CONSTRAINT account_pkey PRIMARY KEY (id);


--
-- Name: contact contact_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.contact
    ADD CONSTRAINT contact_pkey PRIMARY KEY (id);


--
-- Name: el_history__c el_history__c_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.el_history__c
    ADD CONSTRAINT el_history__c_pkey PRIMARY KEY (id);


--
-- Name: event_participant__c event_participant__c_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.event_participant__c
    ADD CONSTRAINT event_participant__c_pkey PRIMARY KEY (id);


--
-- Name: fragforce_event__c fragforce_event__c_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org.fragforce_event__c
    ADD CONSTRAINT fragforce_event__c_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: org; Owner: -
--

ALTER TABLE ONLY org."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: _trigger_log_archive_idx_created_at; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX _trigger_log_archive_idx_created_at ON org._trigger_log_archive USING btree (created_at);


--
-- Name: _trigger_log_archive_idx_record_id; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX _trigger_log_archive_idx_record_id ON org._trigger_log_archive USING btree (record_id);


--
-- Name: _trigger_log_archive_idx_state_table_name; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX _trigger_log_archive_idx_state_table_name ON org._trigger_log_archive USING btree (state, table_name) WHERE ((state)::text = 'FAILED'::text);


--
-- Name: _trigger_log_idx_created_at; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX _trigger_log_idx_created_at ON org._trigger_log USING btree (created_at);


--
-- Name: _trigger_log_idx_state_id; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX _trigger_log_idx_state_id ON org._trigger_log USING btree (state, id);


--
-- Name: _trigger_log_idx_state_table_name; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX _trigger_log_idx_state_table_name ON org._trigger_log USING btree (state, table_name) WHERE (((state)::text = 'NEW'::text) OR ((state)::text = 'PENDING'::text));


--
-- Name: hc_idx_account_el_id__c; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_el_id__c ON org.account USING btree (el_id__c);


--
-- Name: hc_idx_account_lastmodifieddate; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_lastmodifieddate ON org.account USING btree (lastmodifieddate);


--
-- Name: hc_idx_account_masterrecordid; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_masterrecordid ON org.account USING btree (masterrecordid);


--
-- Name: hc_idx_account_name; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_name ON org.account USING btree (name);


--
-- Name: hc_idx_account_ownerid; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_ownerid ON org.account USING btree (ownerid);


--
-- Name: hc_idx_account_parentid; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_parentid ON org.account USING btree (parentid);


--
-- Name: hc_idx_account_recordtypeid; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_recordtypeid ON org.account USING btree (recordtypeid);


--
-- Name: hc_idx_account_systemmodstamp; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_systemmodstamp ON org.account USING btree (systemmodstamp);


--
-- Name: hc_idx_account_type; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_account_type ON org.account USING btree (type);


--
-- Name: hc_idx_contact_systemmodstamp; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_contact_systemmodstamp ON org.contact USING btree (systemmodstamp);


--
-- Name: hc_idx_el_history__c_lastmodifieddate; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_el_history__c_lastmodifieddate ON org.el_history__c USING btree (lastmodifieddate);


--
-- Name: hc_idx_el_history__c_systemmodstamp; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_el_history__c_systemmodstamp ON org.el_history__c USING btree (systemmodstamp);


--
-- Name: hc_idx_event_participant__c_lastmodifieddate; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_event_participant__c_lastmodifieddate ON org.event_participant__c USING btree (lastmodifieddate);


--
-- Name: hc_idx_event_participant__c_systemmodstamp; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_event_participant__c_systemmodstamp ON org.event_participant__c USING btree (systemmodstamp);


--
-- Name: hc_idx_fragforce_event__c_event_end_date__c; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_fragforce_event__c_event_end_date__c ON org.fragforce_event__c USING btree (event_end_date__c);


--
-- Name: hc_idx_fragforce_event__c_event_start_date__c; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_fragforce_event__c_event_start_date__c ON org.fragforce_event__c USING btree (event_start_date__c);


--
-- Name: hc_idx_fragforce_event__c_lastmodifieddate; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_fragforce_event__c_lastmodifieddate ON org.fragforce_event__c USING btree (lastmodifieddate);


--
-- Name: hc_idx_fragforce_event__c_name; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_fragforce_event__c_name ON org.fragforce_event__c USING btree (name);


--
-- Name: hc_idx_fragforce_event__c_site__c; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_fragforce_event__c_site__c ON org.fragforce_event__c USING btree (site__c);


--
-- Name: hc_idx_fragforce_event__c_systemmodstamp; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_fragforce_event__c_systemmodstamp ON org.fragforce_event__c USING btree (systemmodstamp);


--
-- Name: hc_idx_user_systemmodstamp; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX hc_idx_user_systemmodstamp ON org."user" USING btree (systemmodstamp);


--
-- Name: hcu_idx_account_sfid; Type: INDEX; Schema: org; Owner: -
--

CREATE UNIQUE INDEX hcu_idx_account_sfid ON org.account USING btree (sfid);


--
-- Name: hcu_idx_contact_extra_life_id__c; Type: INDEX; Schema: org; Owner: -
--

CREATE UNIQUE INDEX hcu_idx_contact_extra_life_id__c ON org.contact USING btree (extra_life_id__c);


--
-- Name: hcu_idx_contact_sfid; Type: INDEX; Schema: org; Owner: -
--

CREATE UNIQUE INDEX hcu_idx_contact_sfid ON org.contact USING btree (sfid);


--
-- Name: hcu_idx_el_history__c_sfid; Type: INDEX; Schema: org; Owner: -
--

CREATE UNIQUE INDEX hcu_idx_el_history__c_sfid ON org.el_history__c USING btree (sfid);


--
-- Name: hcu_idx_event_participant__c_sfid; Type: INDEX; Schema: org; Owner: -
--

CREATE UNIQUE INDEX hcu_idx_event_participant__c_sfid ON org.event_participant__c USING btree (sfid);


--
-- Name: hcu_idx_fragforce_event__c_sfid; Type: INDEX; Schema: org; Owner: -
--

CREATE UNIQUE INDEX hcu_idx_fragforce_event__c_sfid ON org.fragforce_event__c USING btree (sfid);


--
-- Name: hcu_idx_user_sfid; Type: INDEX; Schema: org; Owner: -
--

CREATE UNIQUE INDEX hcu_idx_user_sfid ON org."user" USING btree (sfid);


--
-- Name: idx__sf_event_log_comp_key; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX idx__sf_event_log_comp_key ON org._sf_event_log USING btree (table_name, synced_at);

--
-- Name: idx__sf_event_log_sfid; Type: INDEX; Schema: org; Owner: -
--

CREATE INDEX idx__sf_event_log_sfid ON org._sf_event_log USING btree (sfid);

--
-- Name: account hc_account_status_trigger; Type: TRIGGER; Schema: org; Owner: -
--

CREATE TRIGGER hc_account_status_trigger BEFORE INSERT OR UPDATE ON org.account FOR EACH ROW EXECUTE FUNCTION org.hc_account_status();

--
-- Name: contact hc_contact_status_trigger; Type: TRIGGER; Schema: org; Owner: -
--

CREATE TRIGGER hc_contact_status_trigger BEFORE INSERT OR UPDATE ON org.contact FOR EACH ROW EXECUTE FUNCTION org.hc_contact_status();

--
-- Name: el_history__c hc_el_history__c_status_trigger; Type: TRIGGER; Schema: org; Owner: -
--

CREATE TRIGGER hc_el_history__c_status_trigger BEFORE INSERT OR UPDATE ON org.el_history__c FOR EACH ROW EXECUTE FUNCTION org.hc_el_history__c_status();

--
-- Name: event_participant__c hc_event_participant__c_status_trigger; Type: TRIGGER; Schema: org; Owner: -
--

CREATE TRIGGER hc_event_participant__c_status_trigger BEFORE INSERT OR UPDATE ON org.event_participant__c FOR EACH ROW EXECUTE FUNCTION org.hc_event_participant__c_status();

--
-- Name: fragforce_event__c hc_fragforce_event__c_status_trigger; Type: TRIGGER; Schema: org; Owner: -
--

CREATE TRIGGER hc_fragforce_event__c_status_trigger BEFORE INSERT OR UPDATE ON org.fragforce_event__c FOR EACH ROW EXECUTE FUNCTION org.hc_fragforce_event__c_status();

--
-- Name: user hc_user_status_trigger; Type: TRIGGER; Schema: org; Owner: -
--

CREATE TRIGGER hc_user_status_trigger BEFORE INSERT OR UPDATE ON org."user" FOR EACH ROW EXECUTE FUNCTION org.hc_user_status();

--
-- Name: _trigger_log tlog_insert_trigger; Type: TRIGGER; Schema: org; Owner: -
--

CREATE TRIGGER tlog_insert_trigger AFTER INSERT ON org._trigger_log FOR EACH ROW EXECUTE FUNCTION org.tlog_notify_trigger();

--
-- PostgreSQL database dump complete
--

ALTER ROLE postgres SET search_path TO org;

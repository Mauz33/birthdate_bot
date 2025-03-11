--
-- PostgreSQL database dump
--

-- Dumped from database version 17.3 (Debian 17.3-3.pgdg120+1)
-- Dumped by pg_dump version 17.3 (Debian 17.3-3.pgdg120+1)

-- Started on 2025-03-04 23:12:12 UTC

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 224 (class 1259 OID 16437)
-- Name: births_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.births_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.births_id_seq OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 217 (class 1259 OID 16393)
-- Name: date_of_births; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.date_of_births (
    id integer DEFAULT nextval('public.births_id_seq'::regclass) NOT NULL,
    celebrant_name text NOT NULL,
    user_id integer,
    day character varying(2) NOT NULL,
    month character varying(2) NOT NULL,
    year character varying(4)
);


ALTER TABLE public.date_of_births OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16435)
-- Name: execution_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.execution_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.execution_id_seq OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16422)
-- Name: execution_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.execution_logs (
    id integer DEFAULT nextval('public.execution_id_seq'::regclass) NOT NULL,
    date timestamp with time zone
);


ALTER TABLE public.execution_logs OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16433)
-- Name: notified_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.notified_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notified_id_seq OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16412)
-- Name: notified_birth_dates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notified_birth_dates (
    id integer DEFAULT nextval('public.notified_id_seq'::regclass) NOT NULL,
    date_of_birth_id integer,
    notify_date timestamp with time zone
);


ALTER TABLE public.notified_birth_dates OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16431)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.users_id_seq OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 16400)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer DEFAULT nextval('public.users_id_seq'::regclass) NOT NULL,
    chat_id integer
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 3230 (class 2606 OID 16399)
-- Name: date_of_births date_of_births_pk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.date_of_births
    ADD CONSTRAINT date_of_births_pk PRIMARY KEY (id);


--
-- TOC entry 3236 (class 2606 OID 16426)
-- Name: execution_logs execution_logs_pk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.execution_logs
    ADD CONSTRAINT execution_logs_pk PRIMARY KEY (id);


--
-- TOC entry 3234 (class 2606 OID 16416)
-- Name: notified_birth_dates notified_birth_dates_pk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notified_birth_dates
    ADD CONSTRAINT notified_birth_dates_pk PRIMARY KEY (id);


--
-- TOC entry 3232 (class 2606 OID 16406)
-- Name: users users_pk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pk PRIMARY KEY (id);


--
-- TOC entry 3238 (class 2606 OID 16417)
-- Name: notified_birth_dates date_of_birth_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notified_birth_dates
    ADD CONSTRAINT date_of_birth_id_fk FOREIGN KEY (date_of_birth_id) REFERENCES public.date_of_births(id) ON DELETE CASCADE;


--
-- TOC entry 3237 (class 2606 OID 16407)
-- Name: date_of_births user_id_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.date_of_births
    ADD CONSTRAINT user_id_fk FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


-- Completed on 2025-03-04 23:12:12 UTC

--
-- PostgreSQL database dump complete
--


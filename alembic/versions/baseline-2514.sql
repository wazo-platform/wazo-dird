-- PostgreSQL database dump

-- Dumped from database version 13.18 (Debian 13.18-0+deb11u1)
-- Dumped by pg_dump version 13.18 (Debian 13.18-0+deb11u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

-- Name: dird_contact; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_contact (
    uuid character varying(38) DEFAULT public.uuid_generate_v4() NOT NULL,
    user_uuid character varying(36),
    hash character varying(40) NOT NULL,
    phonebook_uuid uuid
);

-- Name: dird_contact_fields; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_contact_fields (
    id integer NOT NULL,
    name text NOT NULL,
    value text,
    contact_uuid character varying(38) NOT NULL
);

-- Name: dird_contact_fields_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.dird_contact_fields_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: dird_contact_fields_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.dird_contact_fields_id_seq OWNED BY public.dird_contact_fields.id;

-- Name: dird_display; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_display (
    uuid character varying(36) DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_uuid character varying(36) NOT NULL,
    name text NOT NULL
);

-- Name: dird_display_column; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_display_column (
    uuid character varying(36) DEFAULT public.uuid_generate_v4() NOT NULL,
    display_uuid character varying(36) NOT NULL,
    field text,
    "default" text,
    type text,
    title text,
    number_display text
);

-- Name: dird_favorite; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_favorite (
    contact_id text NOT NULL,
    user_uuid character varying(36) NOT NULL,
    source_uuid character varying(36) NOT NULL
);

-- Name: dird_phonebook; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_phonebook (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    tenant_uuid character varying(36) NOT NULL,
    uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    CONSTRAINT dird_phonebook_name_check CHECK (((name)::text <> ''::text))
);

-- Name: dird_phonebook_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.dird_phonebook_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: dird_phonebook_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.dird_phonebook_id_seq OWNED BY public.dird_phonebook.id;

-- Name: dird_profile; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_profile (
    uuid character varying(36) DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_uuid character varying(36) NOT NULL,
    name text NOT NULL,
    display_uuid character varying(36),
    display_tenant_uuid character varying(36)
);

-- Name: dird_profile_service; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_profile_service (
    uuid character varying(36) DEFAULT public.uuid_generate_v4() NOT NULL,
    profile_uuid character varying(36) NOT NULL,
    service_uuid character varying(36) NOT NULL,
    config json,
    profile_tenant_uuid character varying(36)
);

-- Name: dird_profile_service_source; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_profile_service_source (
    profile_service_uuid character varying(36) NOT NULL,
    source_uuid character varying(36) NOT NULL,
    profile_tenant_uuid character varying(36),
    source_tenant_uuid character varying(36)
);

-- Name: dird_service; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_service (
    uuid character varying(36) DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL
);

-- Name: dird_source; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_source (
    name text DEFAULT public.uuid_generate_v4() NOT NULL,
    uuid character varying(36) DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_uuid character varying(36),
    searched_columns text[],
    first_matched_columns text[],
    format_columns public.hstore,
    extra_fields json,
    backend text NOT NULL,
    phonebook_uuid uuid
);

-- Name: dird_tenant; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_tenant (
    uuid character varying(36) DEFAULT public.uuid_generate_v4() NOT NULL,
    country character varying(2)
);

-- Name: dird_user; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.dird_user (
    user_uuid character varying(36) NOT NULL,
    tenant_uuid character varying(36)
);

-- Name: dird_contact_fields id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_contact_fields ALTER COLUMN id SET DEFAULT nextval('public.dird_contact_fields_id_seq'::regclass);

-- Name: dird_phonebook id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_phonebook ALTER COLUMN id SET DEFAULT nextval('public.dird_phonebook_id_seq'::regclass);

-- Data for Name: dird_contact; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_contact_fields; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_display; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_display_column; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_favorite; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_phonebook; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_profile; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_profile_service; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_profile_service_source; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_service; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_source; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_tenant; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: dird_user; Type: TABLE DATA; Schema: public; Owner: -

-- Name: dird_contact_fields_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -

SELECT pg_catalog.setval('public.dird_contact_fields_id_seq', 1, false);

-- Name: dird_phonebook_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -

SELECT pg_catalog.setval('public.dird_phonebook_id_seq', 1, false);

-- Name: dird_contact_fields dird_contact_fields_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_contact_fields
    ADD CONSTRAINT dird_contact_fields_pkey PRIMARY KEY (id);

-- Name: dird_contact dird_contact_hash_phonebook_uuid; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_contact
    ADD CONSTRAINT dird_contact_hash_phonebook_uuid UNIQUE (phonebook_uuid, hash);

-- Name: dird_contact dird_contact_hash_user_uuid; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_contact
    ADD CONSTRAINT dird_contact_hash_user_uuid UNIQUE (hash, user_uuid);

-- Name: dird_contact dird_contact_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_contact
    ADD CONSTRAINT dird_contact_pkey PRIMARY KEY (uuid);

-- Name: dird_display_column dird_display_column_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_display_column
    ADD CONSTRAINT dird_display_column_pkey PRIMARY KEY (uuid);

-- Name: dird_display dird_display_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_display
    ADD CONSTRAINT dird_display_pkey PRIMARY KEY (uuid);

-- Name: dird_display dird_display_uuid_tenant; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_display
    ADD CONSTRAINT dird_display_uuid_tenant UNIQUE (uuid, tenant_uuid);

-- Name: dird_favorite dird_favorite_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_favorite
    ADD CONSTRAINT dird_favorite_pkey PRIMARY KEY (source_uuid, contact_id, user_uuid);

-- Name: dird_phonebook dird_phonebook_id; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_phonebook
    ADD CONSTRAINT dird_phonebook_id UNIQUE (id);

-- Name: dird_phonebook dird_phonebook_name_tenant_uuid; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_phonebook
    ADD CONSTRAINT dird_phonebook_name_tenant_uuid UNIQUE (name, tenant_uuid);

-- Name: dird_phonebook dird_phonebook_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_phonebook
    ADD CONSTRAINT dird_phonebook_pkey PRIMARY KEY (uuid);

-- Name: dird_phonebook dird_phonebook_tenant_uuid_idx; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_phonebook
    ADD CONSTRAINT dird_phonebook_tenant_uuid_idx UNIQUE (uuid, tenant_uuid);

-- Name: dird_profile dird_profile_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile
    ADD CONSTRAINT dird_profile_pkey PRIMARY KEY (uuid);

-- Name: dird_profile_service dird_profile_service_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile_service
    ADD CONSTRAINT dird_profile_service_pkey PRIMARY KEY (uuid);

-- Name: dird_profile_service dird_profile_service_uuid_tenant; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile_service
    ADD CONSTRAINT dird_profile_service_uuid_tenant UNIQUE (uuid, profile_tenant_uuid);

-- Name: dird_profile dird_profile_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile
    ADD CONSTRAINT dird_profile_tenant_name UNIQUE (tenant_uuid, name);

-- Name: dird_profile dird_profile_uuid_tenant; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile
    ADD CONSTRAINT dird_profile_uuid_tenant UNIQUE (uuid, tenant_uuid);

-- Name: dird_service dird_service_name_key; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_service
    ADD CONSTRAINT dird_service_name_key UNIQUE (name);

-- Name: dird_service dird_service_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_service
    ADD CONSTRAINT dird_service_pkey PRIMARY KEY (uuid);

-- Name: dird_source dird_source_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_source
    ADD CONSTRAINT dird_source_pkey PRIMARY KEY (uuid);

-- Name: dird_source dird_source_tenant_name; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_source
    ADD CONSTRAINT dird_source_tenant_name UNIQUE (tenant_uuid, name);

-- Name: dird_source dird_source_uuid_tenant; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_source
    ADD CONSTRAINT dird_source_uuid_tenant UNIQUE (uuid, tenant_uuid);

-- Name: dird_tenant dird_tenant_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_tenant
    ADD CONSTRAINT dird_tenant_pkey PRIMARY KEY (uuid);

-- Name: dird_user dird_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_user
    ADD CONSTRAINT dird_user_pkey PRIMARY KEY (user_uuid);

-- Name: dird_contact__idx__phonebook_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_contact__idx__phonebook_uuid ON public.dird_contact USING btree (phonebook_uuid);

-- Name: dird_contact__idx__user_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_contact__idx__user_uuid ON public.dird_contact USING btree (user_uuid);

-- Name: dird_contact_fields__idx__contact_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_contact_fields__idx__contact_uuid ON public.dird_contact_fields USING btree (contact_uuid);

-- Name: dird_display__idx__tenant_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_display__idx__tenant_uuid ON public.dird_display USING btree (tenant_uuid);

-- Name: dird_phonebook__idx__tenant_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_phonebook__idx__tenant_uuid ON public.dird_phonebook USING btree (tenant_uuid);

-- Name: dird_profile__idx__display_tenant_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_profile__idx__display_tenant_uuid ON public.dird_profile USING btree (display_tenant_uuid);

-- Name: dird_profile__idx__display_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_profile__idx__display_uuid ON public.dird_profile USING btree (display_uuid);

-- Name: dird_profile__idx__tenant_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_profile__idx__tenant_uuid ON public.dird_profile USING btree (tenant_uuid);

-- Name: dird_profile_service__idx__profile_tenant_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_profile_service__idx__profile_tenant_uuid ON public.dird_profile_service USING btree (profile_tenant_uuid);

-- Name: dird_profile_service__idx__profile_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_profile_service__idx__profile_uuid ON public.dird_profile_service USING btree (profile_uuid);

-- Name: dird_profile_service__idx__service_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_profile_service__idx__service_uuid ON public.dird_profile_service USING btree (service_uuid);

-- Name: dird_source__idx__tenant_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_source__idx__tenant_uuid ON public.dird_source USING btree (tenant_uuid);

-- Name: dird_user__idx__tenant_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX dird_user__idx__tenant_uuid ON public.dird_user USING btree (tenant_uuid);

-- Name: ix_dird_contact_fields_name; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_dird_contact_fields_name ON public.dird_contact_fields USING btree (name);

-- Name: ix_dird_contact_fields_value; Type: INDEX; Schema: public; Owner: -

CREATE INDEX ix_dird_contact_fields_value ON public.dird_contact_fields USING btree (value);

-- Name: dird_contact_fields dird_contact_fields_contact_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_contact_fields
    ADD CONSTRAINT dird_contact_fields_contact_uuid_fkey FOREIGN KEY (contact_uuid) REFERENCES public.dird_contact(uuid) ON DELETE CASCADE;

-- Name: dird_contact dird_contact_phonebook_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_contact
    ADD CONSTRAINT dird_contact_phonebook_uuid_fkey FOREIGN KEY (phonebook_uuid) REFERENCES public.dird_phonebook(uuid) ON DELETE CASCADE;

-- Name: dird_contact dird_contact_user_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_contact
    ADD CONSTRAINT dird_contact_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public.dird_user(user_uuid) ON DELETE CASCADE;

-- Name: dird_display_column dird_display_column_display_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_display_column
    ADD CONSTRAINT dird_display_column_display_uuid_fkey FOREIGN KEY (display_uuid) REFERENCES public.dird_display(uuid) ON DELETE CASCADE;

-- Name: dird_display dird_display_tenant_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_display
    ADD CONSTRAINT dird_display_tenant_uuid_fkey FOREIGN KEY (tenant_uuid) REFERENCES public.dird_tenant(uuid) ON DELETE CASCADE;

-- Name: dird_favorite dird_favorite_source_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_favorite
    ADD CONSTRAINT dird_favorite_source_uuid_fkey FOREIGN KEY (source_uuid) REFERENCES public.dird_source(uuid) ON DELETE CASCADE;

-- Name: dird_favorite dird_favorite_user_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_favorite
    ADD CONSTRAINT dird_favorite_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public.dird_user(user_uuid) ON DELETE CASCADE;

-- Name: dird_phonebook dird_phonebook_tenant_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_phonebook
    ADD CONSTRAINT dird_phonebook_tenant_uuid_fkey FOREIGN KEY (tenant_uuid) REFERENCES public.dird_tenant(uuid) ON DELETE CASCADE;

-- Name: dird_profile dird_profile_display_uuid_tenant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile
    ADD CONSTRAINT dird_profile_display_uuid_tenant_fkey FOREIGN KEY (display_uuid, display_tenant_uuid) REFERENCES public.dird_display(uuid, tenant_uuid) ON DELETE SET NULL;

-- Name: dird_profile_service dird_profile_service_profile_uuid_tenant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile_service
    ADD CONSTRAINT dird_profile_service_profile_uuid_tenant_fkey FOREIGN KEY (profile_uuid, profile_tenant_uuid) REFERENCES public.dird_profile(uuid, tenant_uuid) ON DELETE CASCADE;

-- Name: dird_profile_service dird_profile_service_service_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile_service
    ADD CONSTRAINT dird_profile_service_service_uuid_fkey FOREIGN KEY (service_uuid) REFERENCES public.dird_service(uuid) ON DELETE CASCADE;

-- Name: dird_profile_service_source dird_profile_service_source_profile_service_uuid_tenant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile_service_source
    ADD CONSTRAINT dird_profile_service_source_profile_service_uuid_tenant_fkey FOREIGN KEY (profile_service_uuid, profile_tenant_uuid) REFERENCES public.dird_profile_service(uuid, profile_tenant_uuid) ON DELETE CASCADE;

-- Name: dird_profile_service_source dird_profile_service_source_source_uuid_tenant_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile_service_source
    ADD CONSTRAINT dird_profile_service_source_source_uuid_tenant_fkey FOREIGN KEY (source_uuid, source_tenant_uuid) REFERENCES public.dird_source(uuid, tenant_uuid) ON DELETE CASCADE;

-- Name: dird_profile dird_profile_tenant_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_profile
    ADD CONSTRAINT dird_profile_tenant_uuid_fkey FOREIGN KEY (tenant_uuid) REFERENCES public.dird_tenant(uuid) ON DELETE CASCADE;

-- Name: dird_source dird_source_phonebook_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_source
    ADD CONSTRAINT dird_source_phonebook_fkey FOREIGN KEY (phonebook_uuid, tenant_uuid) REFERENCES public.dird_phonebook(uuid, tenant_uuid) ON DELETE CASCADE;

-- Name: dird_source dird_source_phonebook_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_source
    ADD CONSTRAINT dird_source_phonebook_uuid_fkey FOREIGN KEY (phonebook_uuid) REFERENCES public.dird_phonebook(uuid) ON DELETE CASCADE;

-- Name: dird_source dird_source_tenant_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_source
    ADD CONSTRAINT dird_source_tenant_uuid_fkey FOREIGN KEY (tenant_uuid) REFERENCES public.dird_tenant(uuid);

-- Name: dird_user dird_user_tenant_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.dird_user
    ADD CONSTRAINT dird_user_tenant_uuid_fkey FOREIGN KEY (tenant_uuid) REFERENCES public.dird_tenant(uuid) ON DELETE CASCADE;

-- PostgreSQL database dump complete

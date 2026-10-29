-- TechRook Chatbot — Supabase schema
-- Run this once in: Supabase Dashboard → SQL Editor → New query → Run

create table if not exists users (
  email         text primary key,
  name          text not null,
  password_hash text not null,
  grade         text not null,
  role          text not null,
  dept          text default 'Engineering',
  created_at    timestamptz default now()
);

create table if not exists checklist (
  email     text references users(email) on delete cascade,
  item_id   text,
  completed boolean default false,
  primary key (email, item_id)
);

create table if not exists chat_history (
  id         bigserial primary key,
  email      text references users(email) on delete cascade,
  role       text,
  message    text,
  verified   boolean,
  created_at timestamptz default now()
);

-- Only the backend (service_role key) may touch these tables.
-- With RLS on and no policies, the public anon key gets no access.
alter table users        enable row level security;
alter table checklist    enable row level security;
alter table chat_history enable row level security;
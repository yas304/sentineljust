-- Sentinel Core - Supabase Database Setup
-- Run this SQL in your Supabase SQL Editor

-- Enable the pgvector extension
create extension if not exists vector;

-- Create the clause_embeddings table
create table if not exists clause_embeddings (
    id text primary key,
    clause_text text not null,
    clause_type text not null,
    risk_level text not null,
    issue text,
    recommendation text,
    negotiation_hint text,
    embedding vector(768),
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Create index for vector similarity search
create index if not exists clause_embeddings_embedding_idx 
on clause_embeddings 
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- Create index for clause_type filtering
create index if not exists clause_embeddings_type_idx 
on clause_embeddings(clause_type);

-- Create index for risk_level filtering
create index if not exists clause_embeddings_risk_idx 
on clause_embeddings(risk_level);

-- Create function for vector similarity search
create or replace function match_clauses(
    query_embedding vector(768),
    match_threshold float,
    match_count int
)
returns table (
    id text,
    clause_text text,
    clause_type text,
    risk_level text,
    issue text,
    recommendation text,
    negotiation_hint text,
    similarity float
)
language sql stable
as $$
    select
        clause_embeddings.id,
        clause_embeddings.clause_text,
        clause_embeddings.clause_type,
        clause_embeddings.risk_level,
        clause_embeddings.issue,
        clause_embeddings.recommendation,
        clause_embeddings.negotiation_hint,
        1 - (clause_embeddings.embedding <=> query_embedding) as similarity
    from clause_embeddings
    where 1 - (clause_embeddings.embedding <=> query_embedding) > match_threshold
    order by clause_embeddings.embedding <=> query_embedding
    limit match_count;
$$;

-- Create table for document analysis results (optional, for history)
create table if not exists analysis_history (
    id uuid default gen_random_uuid() primary key,
    document_id text not null,
    filename text not null,
    overall_risk_score float not null,
    risk_summary text,
    clause_count int,
    analysis_result jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- Create index for document lookups
create index if not exists analysis_history_document_idx 
on analysis_history(document_id);

-- Enable Row Level Security (optional but recommended)
alter table clause_embeddings enable row level security;
alter table analysis_history enable row level security;

-- Create policies for anonymous access (adjust as needed for your security requirements)
create policy "Allow anonymous read access to clause_embeddings"
on clause_embeddings for select
to anon
using (true);

create policy "Allow anonymous insert access to clause_embeddings"
on clause_embeddings for insert
to anon
with check (true);

create policy "Allow anonymous read access to analysis_history"
on analysis_history for select
to anon
using (true);

create policy "Allow anonymous insert access to analysis_history"
on analysis_history for insert
to anon
with check (true);

-- Grant necessary permissions
grant usage on schema public to anon;
grant select, insert, update on clause_embeddings to anon;
grant select, insert on analysis_history to anon;
grant execute on function match_clauses to anon;

-- Verify setup
select 'Setup complete! Tables and functions created successfully.' as status;

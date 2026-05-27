create table if not exists documents (
    doc_id text primary key,
    corpus text not null,
    title text,
    source_url text not null,
    source_local_path text,
    source_hash text,
    document_number text,
    legislature text,
    session text,
    published_on text,
    page_count integer,
    raw_text_path text,
    summary_text text,
    tier text not null default 'l0'
);

create table if not exists extracts (
    extract_id text primary key,
    doc_id text not null references documents(doc_id),
    extract_type text,
    title text,
    article_number text,
    speaker text,
    party text,
    pointer text,
    page_start integer,
    page_end integer,
    text_path text,
    verbatim_status text not null default 'deterministic_extract',
    tier text not null default 'l1'
);

create table if not exists derived_artifacts (
    artifact_id text primary key,
    doc_id text references documents(doc_id),
    artifact_type text not null,
    title text,
    source_extract_id text references extracts(extract_id),
    path text not null,
    confidence text,
    tier text not null default 'l2'
);

create table if not exists query_hits (
    query_hash text not null,
    target_id text not null,
    target_type text not null,
    hit_count integer not null default 1,
    primary key (query_hash, target_id, target_type)
);

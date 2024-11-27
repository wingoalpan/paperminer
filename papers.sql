CREATE TABLE if not exists papers (
    paper_id char(20) primary key,
    paper_name varchar(160) not null,
    authors varchar(512),
    abstract text,
    arxiv_id_v varchar(16),
    weblink varchar(50),
    doclink varchar(50),
    paper_pdf varchar(255),
    citations integer,
    publisher varchar(30),
    publish_date varchar(12),
    download_at char(28),
    parseref_at char(28),
    create_at char(28),
    update_at char(28),
    status char(28)
);

CREATE TABLE if not exists refs (
    id integer primary key autoincrement,
    paper_id char(20) not null,
    paper_name varchar(160) not null,
    ref_no integer not null,
    ref_text text not null,
    ref_authors varchar(512),
    ref_id char(20),
    ref_title varchar(160),
    addition varchar(255),
    verified_title varchar(160),
    verify_at char(28),
    create_at char(28),
    update_at char(28),
    status char(28)
);

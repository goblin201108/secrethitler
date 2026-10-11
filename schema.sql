-- Secret Hitler bot — схема БД (Supabase / Postgres)

create table games (
    id uuid primary key default gen_random_uuid(),
    chat_id bigint not null,              -- id группового чата в Telegram
    host_id bigint not null,              -- кто создал партию
    status text not null default 'lobby', -- lobby / nomination / voting / legislative_president /
                                           -- legislative_chancellor / executive / game_over
    player_count int,                     -- фиксируется при старте (5-10)

    -- состояние доски
    liberal_policies int not null default 0,
    fascist_policies int not null default 0,
    election_tracker int not null default 0,
    veto_unlocked boolean not null default false,

    -- колода: массив 'L' / 'F' (liberal/fascist), сверху = последний элемент
    deck jsonb not null default '[]',
    discard jsonb not null default '[]',

    -- текущее правительство
    president_id bigint,
    chancellor_id bigint,
    last_president_id bigint,   -- для проверки term limits
    last_chancellor_id bigint,

    -- карты на руках у президента/канцлера в законодательную сессию
    president_hand jsonb default '[]',
    chancellor_hand jsonb default '[]',

    winner text,                -- 'liberals' / 'fascists' / null пока не закончена
    created_at timestamptz not null default now()
);

create table players (
    id uuid primary key default gen_random_uuid(),
    game_id uuid not null references games(id) on delete cascade,
    user_id bigint not null,
    display_name text not null,
    role text,                  -- 'liberal' / 'fascist' / 'hitler', пусто пока роли не розданы
    is_alive boolean not null default true,
    turn_order int,             -- порядок в очереди на президентство
    joined_at timestamptz not null default now(),

    unique (game_id, user_id)
);

create table votes (
    id uuid primary key default gen_random_uuid(),
    game_id uuid not null references games(id) on delete cascade,
    round_number int not null,       -- сбрасывается/растёт при каждой новой номинации
    voter_id bigint not null,
    vote boolean not null,           -- true = Ja, false = Nein
    voted_at timestamptz not null default now(),

    unique (game_id, round_number, voter_id)
);

create index idx_players_game on players(game_id);
create index idx_votes_game_round on votes(game_id, round_number);

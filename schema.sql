drop table if exists user;
create table user (
  user_id integer primary key autoincrement,
  username text not null,
  email text not null,
  pw_hash text not null
);

drop table if exists follower;
create table follower (
  who_id integer,
  whom_id integer
);

drop table if exists message;
create table message (
  message_id integer primary key autoincrement,
  author_id integer not null,
  text text not null,
  pub_date integer
);

drop table if exists search_score;
create table search_score (
  score_id integer primary key autoincrement,
  query text not null,
  recall float not null,
  semantic_AP float not null,
  baseline_AP float not null,
  semantic_RR float not null,
  baseline_RR float not null,
  semantic_NDCG float not null,
  baseline_NDCG float not null
);

drop table if exists hashtag_score;
create table hashtag_score (
  score_id integer primary key autoincrement,
  query text not null,
  semantic_AP float not null,
  baseline_AP float not null,
  semantic_RR float not null,
  baseline_RR float not null,
  semantic_NDCG float not null,
  baseline_NDCG float not null
);
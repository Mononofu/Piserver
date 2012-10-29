drop table if exists pings;
create table pings (
	id integer primary key autoincrement,
	hostname string not null,
	timestamp integer not null
);

#!/usr/bin/env python3

import sqlite3

conns = dict()

_REG_DB = '/usr/share/cryptobot/history.db'
CURRENT_DB = _REG_DB

# get a cursor
def database(use_file: str=None, read_only: bool=False):
    global conns, CURRENT_DB
    _old_current_db = CURRENT_DB

    if use_file == None:
        use_file = CURRENT_DB
    else:
        CURRENT_DB = use_file

    args = {}
    if read_only:
        args['uri'] = True

    # create the database if not exist
    if not conns.get(use_file):
        conns[use_file] = sqlite3.connect(use_file, detect_types=sqlite3.PARSE_DECLTYPES, **args)

        if not read_only:
            # none of this would be able to run if it was readonly anyway
            _init_database(conns[use_file])

    CURRENT_DB = _old_current_db

    return conns[use_file].cursor()


def close() -> None:
    global conns
    if conns.get(CURRENT_DB):
        retval = conns[CURRENT_DB].close()
        del conns[CURRENT_DB]
        return retval


def commit() -> None:
    global conns
    return conns[CURRENT_DB].commit()


def _init_database(conn) -> None:
    c = conn.cursor()

    c.execute(
        'CREATE TABLE IF NOT EXISTS `orders` ('
        	'`id` INT AUTO_INCREMENT,'
	        '`ts` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,'
	        '`product_id` VARCHAR(10) NOT NULL,'
	        '`order_id` VARCHAR(200) NOT NULL,'
	        '`side` VARCHAR(495),'
	        '`size` DOUBLE,'
	        '`funds` DOUBLE,'
	        #'KEY `id` (`id`) USING BTREE,'
	        'PRIMARY KEY (`id`)'
        ');'
    )

    c.execute(
        'CREATE TABLE IF NOT EXISTS `price_history` ('
	        '`id` INT AUTO_INCREMENT,'
	        '`ts` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,'
	        '`unixts` INT NOT NULL,' # XXX: use TIMESTAMP not INT
	        '`product_id` VARCHAR(10) NOT NULL,'
	        '`spot` DOUBLE NOT NULL,'
	        '`bid` DOUBLE,'
	        '`ask` DOUBLE,'
	        '`volume` DOUBLE,'
	        '`source` VARCHAR(10) NOT NULL,'
	        'PRIMARY KEY (`id`)'
        ');'
    )

    c.execute(
        'CREATE TABLE IF NOT EXISTS `portfolio_history` ('
	        '`id` INT AUTO_INCREMENT,'
	        '`ts` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,'
	        '`product_id` VARCHAR(10) NOT NULL,'
	        '`coin` DOUBLE NOT NULL,'
	        '`usd` DOUBLE NOT NULL,'
	        'PRIMARY KEY (`id`)'
        ');'
    )

    c.execute(
        'CREATE TABLE IF NOT EXISTS `movement_score_history` ('
	        '`id` INT AUTO_INCREMENT,'
	        '`ts` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,'
	        '`product_id` VARCHAR(10) NOT NULL,'
	        '`score` DOUBLE NOT NULL,'
	        'PRIMARY KEY (`id`)'
        ');'
    )

    commit()
    c.close()

#!/usr/bin/env python3

import sqlite3

conn = None

# get a cursor
def database():
    global conn
    
    # create the database if not exist
    if not conn:
        conn = sqlite3.connect('/usr/share/cryptobot/history.db', detect_types=sqlite3.PARSE_DECLTYPES)
        _init_database(conn)
    
    return conn.cursor()


def commit():
    global conn
    return conn.commit()


def _init_database(conn):
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

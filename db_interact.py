import sqlite3

connection = sqlite3.connect('database.db')
cursor = connection.cursor()

def reg_user(chat_id):
    res = cursor.execute(f"""
    SELECT COUNT(*) FROM users 
    WHERE chat_id = {chat_id}""").fetchone()

    if res[0] == 0:
        cursor.execute(f"""
        insert into users (chat_id) 
        values ({chat_id});""")
        connection.commit()


def add_birth(chat_id, celebrant, date):
    res = cursor.execute(f"""
    SELECT id FROM users 
    WHERE chat_id = {chat_id}""").fetchone()

    if res:
        cursor.execute(f"""
        insert into date_of_births 
        (celebrant_name, day, month, year, user_id) 
        values (?, ?, ?, ?, ?);""",
        (celebrant, date[0], date[1], date[2], res[0]))
        connection.commit()


def get_births_by_chat_id(chat_id):
    query1 = cursor.execute(f"""
    SELECT id FROM users 
    WHERE chat_id = {chat_id}""").fetchone()
    res = []

    if query1:
        user_id = query1[0]
        res = cursor.execute(f"""
        SELECT * FROM date_of_births 
        WHERE user_id = {user_id} 
        ORDER BY month, day""").fetchall()

    return res

def check_is_user_own_row(chat_id, row_id):
    query = cursor.execute(f"""
    SELECT COUNT() FROM date_of_births as d 
    JOIN main.users as u on u.id = d.user_id 
    where d.id = {row_id} and u.chat_id = {chat_id}""").fetchone()

    return True if query[0] == 1 else False

def delete_birth_row(row_id):
    query = cursor.execute(f"""
        DELETE FROM date_of_births WHERE id = {row_id}""")

# def delete_row_by_id(chat_id, row_id)

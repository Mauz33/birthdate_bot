import sqlite3
from collections import defaultdict

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


columns_1 = ["id", "celebrant_name", "user_id", "day", "month", "year"]
def get_births_by_chat_id(chat_id):

    query1 = cursor.execute(f"""
    SELECT id FROM users 
    WHERE chat_id = {chat_id}""").fetchone()

    grouped = defaultdict(list)
    if query1:
        user_id = query1[0]
        res = cursor.execute(f"""
        SELECT * FROM date_of_births 
        WHERE user_id = {user_id} 
        ORDER BY month, day""").fetchall()

        for x in res:
            month = x[4]
            grouped[month].append(dict(zip(columns_1, x)))

    return grouped

def check_is_user_own_row(chat_id, row_id):
    query = cursor.execute(f"""
    SELECT COUNT() FROM date_of_births as d 
    JOIN main.users as u on u.id = d.user_id 
    where d.id = {row_id} and u.chat_id = {chat_id}""").fetchone()

    return True if query[0] == 1 else False

def delete_birth_row(row_id):
    query = cursor.execute(f"""
        DELETE FROM date_of_births WHERE id = {row_id}""")

columns_2 = ["id", "celebrant_name", "nearest_date", "days_until"]
def get_rows_the_next_n_days(chat_id, next_n_days):
    res = cursor.execute(
        f"""
        WITH births as (
        select
        *,
        CASE WHEN julianday(DATE('now')) > julianday(strftime('%Y', 'now') || '-' || d.month || '-' || d.day)
            THEN strftime('%Y', 'now', '+1 years') || '-' || d.month || '-' || d.day
            ELSE strftime('%Y', 'now') || '-' || d.month || '-' || d.day
        END AS nearest_date
        from date_of_births d
        join main.users u on d.user_id = u.id
        where u.chat_id = {chat_id} AND julianday(nearest_date) - julianday(date('now')) between 0 and {next_n_days}
        )
        
        SELECT
            b.id,
            b.celebrant_name,
            strftime('%d.%m.%Y', b.nearest_date),
            julianday(b.nearest_date) - julianday(date('now')) as days_until
        FROM births b
        """
    ).fetchall()

    arr = []
    for x in res:
        arr.append(dict(zip(columns_2, x)))

    return arr

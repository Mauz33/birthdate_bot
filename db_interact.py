from datetime import datetime as dt
import sqlite3

from utils import convert_tuple_to_dict_with_custom_columns

connection = sqlite3.connect('database.db')
cursor = connection.cursor()


async def reg_user(chat_id: int):
    res = cursor.execute(f"""
    SELECT COUNT(*) FROM users 
    WHERE chat_id = {chat_id}""").fetchone()

    if res[0] == 0:
        cursor.execute(f"""
        insert into users (chat_id) 
        values ({chat_id});""")
        connection.commit()


async def add_birth(chat_id: int, celebrant: str, date: str) -> int:
    query = cursor.execute(f"""
    SELECT id FROM users 
    WHERE chat_id = {chat_id}""").fetchone()

    user_id = query[0]

    if user_id:
        cursor.execute(f"""
        insert into date_of_births 
        (celebrant_name, day, month, year, user_id) 
        values (?, ?, ?, ?, ?);""",
        (celebrant, date[0], date[1], date[2], user_id))

        id = cursor.lastrowid
        connection.commit()

        return id



columns_1 = ["id", "celebrant_name", "user_id", "day", "month", "year"]
async def get_births_by_chat_id(chat_id: int) -> dict[str, list[dict]]:
    query1 = cursor.execute(f"""
    SELECT id FROM users 
    WHERE chat_id = {chat_id}""").fetchone()

    grouped = {}
    if query1:
        user_id = query1[0]
        res = cursor.execute(f"""
        SELECT * FROM date_of_births 
        WHERE user_id = {user_id} 
        ORDER BY month, day""").fetchall()

        grouped = await convert_tuple_to_dict_with_custom_columns(query=res, columns=columns_1, key_index=columns_1.index('month'))

    return grouped


async def check_is_user_own_row(chat_id: int, row_id: int) -> bool:
    query = cursor.execute(f"""
    SELECT COUNT() FROM date_of_births as d 
    JOIN main.users as u on u.id = d.user_id 
    where d.id = {row_id} and u.chat_id = {chat_id}""").fetchone()

    return True if query[0] == 1 else False


async def delete_birth_row(row_id: int) -> None:
    query = cursor.execute(f"""
        DELETE FROM date_of_births WHERE id = {row_id}""")
    print('1')


columns_2 = ["id", "celebrant_name", "nearest_date", "days_until"]
async def get_rows_the_next_n_days(chat_id: int, next_n_days: int) -> list[dict]:
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


async def save_notification(date_of_birth_id: int, today: str) -> None:
    cursor.execute(
        f"""
            insert into notified_birth_dates (date_of_birth_id, notify_date)
            values ({date_of_birth_id}, '{today}');
        """
    )
    connection.commit()


columns_3 = ["date_of_birth_id", "chat_id", "celebrant_name", "day_month", "year", "nearest_date", "days_until"]
async def get_none_notified_birthdate_in_interval(interval_from: int, interval_to: int) -> dict[str, list[dict]]:
    query = cursor.execute(
        f"""
            select
            d.id,
            u.chat_id,
            d.celebrant_name,
            d.day || '.' || d.month as day_month,
            d.year,
            CASE WHEN julianday(DATE('now')) > julianday(strftime('%Y', 'now') || '-' || d.month || '-' || d.day)
                THEN strftime('%Y', 'now', '+1 years') || '-' || d.month || '-' || d.day
                ELSE strftime('%Y', 'now') || '-' || d.month || '-' || d.day
            END AS nearest_date,
            julianday(
                CASE WHEN julianday(DATE('now')) > julianday(strftime('%Y', 'now') || '-' || d.month || '-' || d.day)
                    THEN strftime('%Y', 'now', '+1 years') || '-' || d.month || '-' || d.day
                    ELSE strftime('%Y', 'now') || '-' || d.month || '-' || d.day
                END
            ) - julianday(date('now')) as days_until
            FROM date_of_births as d
            JOIN users u on u.id = d.user_id
            LEFT JOIN notified_birth_dates nbd on d.id = nbd.date_of_birth_id
            where julianday(nearest_date) - julianday(date('now')) BETWEEN {interval_from} AND {interval_to}
              AND (nbd.notify_date is NULL OR (julianday(nearest_date) - julianday(
                    (select max(n.notify_date)
                     from notified_birth_dates as n
                     where n.date_of_birth_id = d.id)
                                                    )) NOT BETWEEN {interval_from} AND {interval_to})
                                                    group by d.id;
            """
    ).fetchall()

    grouped = await convert_tuple_to_dict_with_custom_columns(query=query, columns=columns_3,
                                                        key_index=columns_3.index('chat_id'))

    return grouped

async def get_concrete_none_notified_birthdate_in_interval(interval_from: int, interval_to: int, birth_date_id: int):
    query = cursor.execute(
        f"""
                WITH specific_date as (
                    SELECT
                    d.id,
                    d.user_id,
                    d.celebrant_name,
                    d.day || '.' || d.month as day_month,
                    d.year,
                    CASE WHEN julianday(DATE('now')) > julianday(strftime('%Y', 'now') || '-' || d.month || '-' || d.day)
                        THEN strftime('%Y', 'now', '+1 years') || '-' || d.month || '-' || d.day
                        ELSE strftime('%Y', 'now') || '-' || d.month || '-' || d.day
                    END AS nearest_date,
                    julianday(
                        CASE WHEN julianday(DATE('now')) > julianday(strftime('%Y', 'now') || '-' || d.month || '-' || d.day)
                            THEN strftime('%Y', 'now', '+1 years') || '-' || d.month || '-' || d.day
                            ELSE strftime('%Y', 'now') || '-' || d.month || '-' || d.day
                        END
                    ) - julianday(date('now')) as days_until
                    FROM date_of_births as d
                    where d.id = {birth_date_id}
                )
                SELECT
                    s.id,
                    u.chat_id,
                    s.celebrant_name,
                    s.day_month,
                    s.year,
                    s.nearest_date,
                    s.days_until
                FROM specific_date as s
                JOIN users u on u.id = s.user_id
                LEFT JOIN notified_birth_dates nbd on s.id = nbd.date_of_birth_id
                where julianday(nearest_date) - julianday(date('now')) BETWEEN {interval_from} AND {interval_to}
                  AND (nbd.notify_date is NULL OR (julianday(nearest_date) - julianday(
                        (select max(n.notify_date)
                         from notified_birth_dates as n
                         where n.date_of_birth_id = s.id)
                                                        )) NOT BETWEEN {interval_from} AND {interval_to})
                """
    ).fetchall()

    grouped = await convert_tuple_to_dict_with_custom_columns(query=query, columns=columns_3,
                                                              key_index=columns_3.index('chat_id'))

    return grouped


columns_4 = ["date_of_birth_id", "chat_id", "celebrant_name", "date", "days_ago"]
async def get_missed_births():
    query = cursor.execute("SELECT date(max(julianday(date))) from launch_logs").fetchone()
    last_launch = query[0]
    if not last_launch:
        last_launch = dt.now().strftime("%Y-%m-%d")

    # TODO: для простоты и отсутсвия спама с опорой на реальность, что сервер не будет лежать
    #  большего года обрабатывается год последнего запуска и текущий год (для обработки перехода между годами) для поиска пропущенных уведомлений
    #  На перспективу: при занесении новой даты в базу - прописывать дату её создания, чтобы обрабатывать все промущенные года, но будто пофиг
    sql_q = f"""
            WITH dates AS (
            SELECT
                id,
                celebrant_name,
                day,
                month,
                julianday(date(printf('%d-%02d-%02d', strftime('%Y', '{last_launch}'), month, day))) AS bday_last_year,
                julianday(date(printf('%d-%02d-%02d', strftime('%Y', 'now'), month, day))) AS bday_this_year
            FROM date_of_births
            )

            SELECT d.id, u.chat_id, db.celebrant_name, date(bday_last_year) as date, julianday(date('now')) - bday_last_year AS days_ago
            FROM dates d
            LEFT JOIN notified_birth_dates nbd on nbd.date_of_birth_id = d.id
            JOIN date_of_births db on db.id = d.id
            JOIN main.users u on u.id = db.user_id
                -- Нужно получить такие ДР, которые попадают в диапазон между last_launch и сегодня,
                -- и при left_join либо о них еще не уведомляли ни разу (nbd.notify_date is null) либо дата уведомления
                -- в диапазоне между last_launch и сегодня меньше, чем дата ДР
            WHERE bday_last_year > julianday('{last_launch}') AND bday_last_year < julianday(date('now')) AND (nbd.notify_date is null or julianday(nbd.notify_date) < bday_last_year)

            UNION

            SELECT d.id, u.chat_id, db.celebrant_name, date(bday_this_year) as date, julianday(date('now')) - bday_this_year AS days_ago
            FROM dates d
            LEFT JOIN notified_birth_dates nbd on nbd.date_of_birth_id = d.id
            JOIN date_of_births db on db.id = d.id
            JOIN main.users u on u.id = db.user_id
            WHERE bday_this_year > julianday('{last_launch}') AND bday_this_year < julianday(date('now')) AND (nbd.notify_date is null or julianday(nbd.notify_date) < bday_last_year)
            """

    query = cursor.execute(sql_q).fetchall()

    grouped = await convert_tuple_to_dict_with_custom_columns(query=query, columns=columns_4,
                                                        key_index=columns_4.index('chat_id'))

    return grouped


async def fill_last_launch_log():
    cursor.execute(
        f"""
    insert into launch_logs
    (date) 
    values ('{dt.now().strftime("%Y-%m-%d")}');
    """, )
    connection.commit()

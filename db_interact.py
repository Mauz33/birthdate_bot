import datetime
from datetime import datetime as dt

import psycopg2 as psycopg2

from utils import convert_tuple_to_dict_with_custom_columns


class DBService:
    def __init__(self, **kwargs):
        """Создает подключение к БД"""
        self.conn = psycopg2.connect(**kwargs)
        self.cur = self.conn.cursor()

    def execute_query(self, query: str, params=None):
        """Выполняет запрос и коммитит изменения, если нужно"""
        self.cur.execute(query, params or ()) # если используется returning
        self.conn.commit()

    def fetch_all(self, query: str, params=None):
        """Выполняет SELECT-запрос и возвращает все результаты"""
        self.cur.execute(query, params or ())
        return self.cur.fetchall()

    def fetch_one(self, query: str, params=None):
        """Выполняет SELECT-запрос и возвращает одну строку"""
        self.cur.execute(query, params or ())
        return self.cur.fetchone()

    def close(self):
        """Закрывает соединение"""
        self.cur.close()
        self.conn.close()


__db_instance: DBService = None

def configure_db_instance():
    try:
        con_dict = {
            "host": "localhost",
            "port": "5432",
            "database": "birth_bot",
            "user": "postgres",
            "password": "mysecretpassword"
        }
        global __db_instance
        __db_instance = DBService(**con_dict)
        print("Database connected successfully")

    except:
        print("Database not connected successfully")


def get_db_instance():
    configure_db_instance()
    if __db_instance:
        return __db_instance
    else:
        print(f"In first call {configure_db_instance.__name__}")

async def reg_user(db_instance: DBService, chat_id: int):
    query = f"""
    SELECT COUNT(*) FROM users 
    WHERE chat_id = {chat_id}"""

    res = db_instance.fetch_one(query)

    if res[0] == 0:
        db_instance.execute_query(f"""
        insert into users (chat_id) 
        values ({chat_id});""")


async def add_birth(db_instance: DBService, chat_id: int, celebrant: str, date: str) -> int:
    res = db_instance.fetch_one(f"""
    SELECT id FROM users 
    WHERE chat_id = {chat_id}""")

    user_id = res[0]

    if user_id:
        db_instance.execute_query(f"""
        insert into date_of_births 
        (celebrant_name, day, month, year, user_id) 
        values (%s, %s, %s, %s, %s) RETURNING id;""",
                    (celebrant, date[0], date[1], date[2], user_id))

        row_id = db_instance.cur.fetchone()[0]
        # connection.commit()

        return row_id


columns_1 = ["id", "celebrant_name", "user_id", "day", "month", "year"]
async def get_births_by_chat_id(db_instance: DBService, chat_id: int) -> dict[str, list[dict]]:
    fetched_user_id_query = db_instance.fetch_one(f"""
    SELECT id FROM users 
    WHERE chat_id = {chat_id}""")

    grouped = {}
    if fetched_user_id_query:
        user_id = fetched_user_id_query[0]
        fetched_date_of_births = db_instance.fetch_all(f"""
        SELECT * FROM date_of_births 
        WHERE user_id = {user_id} 
        ORDER BY month, day""")

        grouped = await convert_tuple_to_dict_with_custom_columns(query=fetched_date_of_births, columns=columns_1,
                                                                  key_index=columns_1.index('month'))

    return grouped


async def check_is_user_own_row(db_instance: DBService, chat_id: int, row_id: int) -> bool:
    fetched_is_owner = db_instance.fetch_one(f"""
    SELECT COUNT() FROM date_of_births as d 
    JOIN main.users as u on u.id = d.user_id 
    where d.id = {row_id} and u.chat_id = {chat_id}""")

    return True if fetched_is_owner[0] == 1 else False


async def delete_birth_row(db_instance: DBService, row_id: int) -> None:
    db_instance.execute_query(f"""
        DELETE FROM date_of_births WHERE id = {row_id}""")


columns_2 = ["id", "celebrant_name", "nearest_date", "days_until"]
async def get_rows_the_next_n_days(db_instance: DBService, chat_id: int, next_n_days: int) -> list[dict]:
    res = db_instance.fetch_all(
        f"""
        WITH births as (
            select
            d.id,
            d.celebrant_name,
            u.chat_id,
            CASE WHEN CURRENT_DATE > (extract(year from current_date) || '-' || d.month || '-' || d.day)::date
                THEN (extract(year from current_date + interval '1 year') || '-' || d.month || '-' || d.day)::date
                ELSE (extract(year from current_date) || '-' || d.month || '-' || d.day)::date
            END AS nearest_date
            from date_of_births d
            join users u on d.user_id = u.id
        )
        
        SELECT
            b.id,
            b.celebrant_name,
            to_char(b.nearest_date, 'mm.dd.YYYY'),
            b.nearest_date - current_date as days_until
        FROM births b
        where b.chat_id = {chat_id} AND nearest_date - current_date between 0 and {next_n_days}
        ORDER BY days_until
        """
    )

    arr = []
    for x in res:
        arr.append(dict(zip(columns_2, x)))

    return arr


async def save_notification(db_instance: DBService, date_of_birth_id: int) -> None:
    db_instance.execute_query(
        f"""
            insert into notified_birth_dates (date_of_birth_id, notify_date)
            values ({date_of_birth_id}, current_timestamp);
        """
    )


columns_3 = ["date_of_birth_id", "chat_id", "celebrant_name", "day_month", "year", "nearest_date", "days_until"]


async def get_none_notified_birthdate_in_interval(db_instance: DBService, interval_from: int, interval_to: int) -> dict[
    str, list[dict]]:
    fetched_non_notified_dates_in_interval = db_instance.fetch_all(
        f"""
            WITH dates as (
            select
            d.id,
            d.user_id,
            d.celebrant_name,
            d.day || '.' || d.month as day_month,
            d.year,
            make_date(extract(year from current_date)::int +
                      case when current_date > make_date(extract(year from current_date)::int, d.month::int, d.day::int)
                        then 1
                        else 0
                      end, d.month::int, d.day::int
            ) as nearest_date
            FROM date_of_births as d
        )
        
        SELECT
            dt.id,
            u.chat_id,
            dt.celebrant_name,
            dt.day_month,
            dt.year,
            dt.nearest_date,
            dt.nearest_date - current_date as days_until
            FROM dates as dt
        JOIN users u on u.id = dt.user_id
        LEFT JOIN notified_birth_dates nbd on dt.id = nbd.date_of_birth_id
        where dt.nearest_date - current_date BETWEEN {interval_from} AND {interval_to}
        AND (nbd.notify_date is NULL OR (dt.nearest_date - (select max(n.notify_date)
                                                             from notified_birth_dates as n
                                                             where n.date_of_birth_id = dt.id)::date
                                            ) NOT BETWEEN {interval_from} AND {interval_to})
         """
    )

    grouped = await convert_tuple_to_dict_with_custom_columns(query=fetched_non_notified_dates_in_interval,
                                                              columns=columns_3,
                                                              key_index=columns_3.index('chat_id'))

    return grouped


async def get_concrete_none_notified_birthdate_in_interval(db_instance: DBService, interval_from: int, interval_to: int,
                                                           birth_date_id: int):
    fetched_date = db_instance.fetch_all(
        f"""
                WITH specific_date as (
                SELECT
                d.id,
                d.user_id,
                d.celebrant_name,
                d.day || '.' || d.month as day_month,
                d.year,
                make_date(extract(year from current_date)::int +
                          case when current_date > make_date(extract(year from current_date)::int, d.month::int, d.day::int)
                            then 1
                            else 0
                          end, d.month::int, d.day::int
                ) as nearest_date
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
                nearest_date-current_date as days_until
            FROM specific_date as s
            JOIN users u on u.id = s.user_id
            LEFT JOIN notified_birth_dates nbd on s.id = nbd.date_of_birth_id
            where nearest_date - current_date BETWEEN {interval_from} AND {interval_to}
              AND (nbd.notify_date is NULL OR (nearest_date -   (select max(n.notify_date)
                                                                 from notified_birth_dates as n
                                                                 where n.date_of_birth_id = s.id)::date
                                                    ) NOT BETWEEN {interval_from} AND {interval_to});
                """
    )

    grouped = await convert_tuple_to_dict_with_custom_columns(query=fetched_date, columns=columns_3,
                                                              key_index=columns_3.index('chat_id'))

    return grouped


# NOTE: ДЕБАЖНЫЙ КОД С ИНТЕРВАЛ +1 МЕСЯЦ.  ... < current_date + interval '1 month'
columns_4 = ["date_of_birth_id", "chat_id", "celebrant_name", "date", "days_ago"]
async def get_missed_births(db_instance: DBService):
    fetched_last_launch_date = db_instance.fetch_one("SELECT max(e.date) from execution_logs as e")
    last_launch_obj = fetched_last_launch_date[0]
    if not last_launch_obj:
        last_launch_obj = dt.now()

    last_launch = dt.strftime(last_launch_obj, '%Y-%m-%d')

    # TODO: для простоты и отсутсвия спама с опорой на реальность, что сервер не будет лежать
    #  большего года - обрабатывается год последнего запуска и текущий год (для обработки перехода между годами) для поиска пропущенных уведомлений
    #  На перспективу: при занесении новой даты в базу - прописывать дату её создания, чтобы обрабатывать все промущенные года, но будто пофиг
    sql_q = f"""
            WITH dates AS (
            SELECT
                id,
                celebrant_name,
                day,
                month,
                (extract(year from '{last_launch}'::date) || '-' || month || '-' || day)::date AS bday_last_year,
                (extract(year from current_date) || '-' || month || '-' || day)::date AS bday_this_year
            FROM date_of_births
            )
        
            SELECT d.id, u.chat_id, db.celebrant_name, bday_last_year as date, current_date - bday_last_year AS days_ago
            FROM dates d
            LEFT JOIN notified_birth_dates nbd on nbd.date_of_birth_id = d.id
            JOIN date_of_births db on db.id = d.id
            JOIN users u on u.id = db.user_id
                -- Нужно получить такие ДР, которые попадают в диапазон между last_launch и сегодня,
                -- и при left_join либо о них еще не уведомляли ни разу (nbd.notify_date is null) либо дата уведомления
                -- в диапазоне между last_launch и сегодня меньше, чем дата ДР
            WHERE bday_last_year > '{last_launch}'::date AND bday_last_year < current_date AND (nbd.notify_date is null or nbd.notify_date < bday_last_year)
        
            UNION
        
            SELECT d.id, u.chat_id, db.celebrant_name, bday_this_year as date, current_date - bday_this_year AS days_ago
            FROM dates d
            LEFT JOIN notified_birth_dates nbd on nbd.date_of_birth_id = d.id
            JOIN date_of_births db on db.id = d.id
            JOIN users u on u.id = db.user_id
            WHERE bday_this_year > '{last_launch}'::date AND bday_this_year < current_date AND (nbd.notify_date is null or nbd.notify_date < bday_this_year);
            """

    fetched_missed_dates = db_instance.fetch_all(sql_q)

    grouped = await convert_tuple_to_dict_with_custom_columns(query=fetched_missed_dates, columns=columns_4,
                                                              key_index=columns_4.index('chat_id'))

    return grouped


async def fill_last_launch_log(db_instance: DBService):
    db_instance.execute_query(
        f"""
    insert into execution_logs
    (date) 
    values (current_timestamp);
    """, )

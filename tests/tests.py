from __future__ import annotations
import utils

from datetime import datetime, timedelta
from db.db_interact import DBService, check_is_user_own_row, get_rows_the_next_n_days, get_births_by_chat_id, \
    get_none_notified_birthdate_in_interval, save_notification, get_missed_births, configure_db_instance, get_db_instance
import pytest

import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='../.env')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')
OUTER_PORT = os.getenv('OUTER_PORT')

@pytest.fixture(scope="session")
def db_connection():
    try:
        """Фикстура устанавливает соединение с тестовой базой."""
        configure_db_instance(OUTER_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)
        db_service: DBService = get_db_instance()

        # cur.execute(""" insert into users (chat_id)
        #                 values (%s)
        #             """, (10000,))
        # conn.commit()

        # t = []
        # for i in range(0, 15):
        #     date = datetime.now() + timedelta(days=i)
        #     t.append((f"celebrant {i}", 1, f"{date.day:02d}", f"{date.month:02d}", 'NULL'))
        #
        # cur.executemany("""insert into date_of_births (celebrant_name, user_id, day, month, year)
        #                    values (%s, %s, %s, %s, %s)
        #                 """, t)
        # conn.commit()

        print('nice db')
        yield db_service
        db_service.close()
    except:
        print('bad db')

# Фикстура для очистки базы данных перед каждым тестом (scope="function")
@pytest.fixture(scope="function")
def clean_db(db_connection):
    # Очищаем базу данных перед каждым тестом
    db_connection.execute_query("TRUNCATE TABLE users CASCADE")
    db_connection.execute_query("TRUNCATE TABLE date_of_births CASCADE")
    db_connection.execute_query("TRUNCATE TABLE notified_birth_dates CASCADE")
    db_connection.execute_query("TRUNCATE TABLE execution_logs CASCADE")
    yield  # Тест выполняется здесь


class TestSql:
    @pytest.mark.asyncio
    async def test_check_is_user_own_row(self, db_connection: DBService, clean_db):
        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10001,))
        user1_id = db_connection.cur.fetchone()[0]

        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10002,))
        user2_id = db_connection.cur.fetchone()[0]

        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year)
                               values (%s, %s, %s, %s, %s) RETURNING id""", ("", user1_id, "", "", ""))
        row1_id = db_connection.cur.fetchone()[0]

        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year)
                                       values (%s, %s, %s, %s, %s) RETURNING id""", ("", user2_id, "", "", ""))
        row2_id = db_connection.cur.fetchone()[0]

        assert await check_is_user_own_row(db_connection, 10001, row1_id)
        assert await check_is_user_own_row(db_connection, 10002, row2_id)

        assert not await check_is_user_own_row(db_connection, 10001, row2_id)
        assert not await check_is_user_own_row(db_connection, 10002, row1_id)

        assert not await check_is_user_own_row(db_connection, -1, -1)

    @pytest.mark.asyncio
    async def test_get_rows_the_next_n_days(self, db_connection: DBService, clean_db):
        arr = [
            {
                "n_rows": 30,
                "chat_id": 10001,
                "current_date": "2025-12-25",
                "next_n_days": 29,
                "expected": 30
            },
            {
                "n_rows": 5,
                "chat_id": 10002,
                "current_date": "2025-12-25",
                "next_n_days": 60,
                "expected": 5
            },
            {
                "n_rows": 0,
                "chat_id": 10003,
                "current_date": "2025-12-25",
                "next_n_days": 0,
                "expected": 0
            }
        ]

        for i in range(len(arr)):
            db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (arr[i]['chat_id'],))
            user1_id = db_connection.cur.fetchone()[0]
            arr[i]['user_id'] = user1_id
            add_n_rows_to_user(n_rows=arr[i]['n_rows'], user_id=user1_id, db_connection=db_connection, current_date=arr[i]['current_date'])
            res = len(await get_rows_the_next_n_days(db_instance=db_connection, chat_id=arr[i]['chat_id'], next_n_days=arr[i]['next_n_days'], current_date=arr[i]['current_date']))
            assert res == arr[i]['expected']

    @pytest.mark.asyncio
    async def test_get_births_by_chat_id(self, db_connection: DBService, clean_db):
        arr = [
            {
                "chat_id": 10001,
                "current_date": "2025-12-25",
                "add_n_rows": 4,
            },
            {
                "chat_id": 10002,
                "current_date": "2025-12-25",
                "add_n_rows": 3,
            }
        ]

        for i in range(len(arr)):
            db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (arr[i]['chat_id'],))
            user_id = db_connection.cur.fetchone()[0]
            arr[i]['user_id'] = user_id

        for i in range(len(arr)):
            add_n_rows_to_user(n_rows=arr[i]['add_n_rows'], user_id=arr[i]['user_id'], db_connection=db_connection, current_date=arr[i]['current_date'])

        for i in range(len(arr)):
            res = await get_births_by_chat_id(db_instance=db_connection, chat_id=arr[i]['chat_id'])
            flat_array = sum([y for x, y in res.items()], [])
            filtered = filter(lambda x: x['user_id'] == arr[i]['user_id'], flat_array)
            len_with_right_user_id = len(list(filtered))
            assert len_with_right_user_id == arr[i]['add_n_rows']


class TestSql_get_none_notified_birthdate_in_interval:
    @pytest.mark.asyncio
    # ДР в периоде, но нет уведомлений в целом
    async def test_birth_in_interval_and_no_have_notif(self, db_connection: DBService, clean_db):
        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10001,))
        user1_id: int = db_connection.cur.fetchone()[0]

        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10002,))
        user2_id: int = db_connection.cur.fetchone()[0]

        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                        values (%s, %s, %s, %s, %s)""", ('', user2_id, '25', '12', ''))

        current_date = '2025-12-25'
        # date = datetime.strptime(current_date, '%Y-%m-%d')
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                values (%s, %s, %s, %s, %s)""", ('', user1_id, '24', '12', ''))
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                        values (%s, %s, %s, %s, %s)""", ('', user1_id, '25', '12', ''))
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                values (%s, %s, %s, %s, %s)""", ('', user1_id, '22', '07', ''))

        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 0, current_date)
        assert len(res[10001]) == 1
        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 5, current_date)
        assert len(res[10001]) == 1
        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 30, current_date)
        assert len(res[10001]) == 1
        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 300, current_date)
        assert len(res[10001]) == 2
        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 365, current_date)
        assert len(res[10001]) == 3

    # ДР не в периоде
    @pytest.mark.asyncio
    async def test_birth_in_interval_and_no_have_notif(self, db_connection: DBService, clean_db):
        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10001,))
        user1_id: int = db_connection.cur.fetchone()[0]


        current_date = '2025-12-25'
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                        values (%s, %s, %s, %s, %s)""",
                                    ('', user1_id, '24', '12', ''))


        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 0, current_date)
        assert 10001 not in res
        res = await get_none_notified_birthdate_in_interval(db_connection, 1, 5, current_date)
        assert 10001 not in res
        res = await get_none_notified_birthdate_in_interval(db_connection, 12, 34, current_date)
        assert 10001 not in res
        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 360, current_date)
        assert 10001 not in res

    @pytest.mark.asyncio
    # ДР в периоде, есть уведомления, но не в указанном периоде
    async def test_birth_in_interval_and_have_notif_not_in_interval(self, db_connection: DBService, clean_db):
        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10001,))
        user1_id: int = db_connection.cur.fetchone()[0]
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                        values (%s, %s, %s, %s, %s) RETURNING id""", ('', user1_id, '14', '01', ''))
        date_of_b_id1 = db_connection.cur.fetchone()[0]

        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10002,))
        user2_id: int = db_connection.cur.fetchone()[0]
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                                values (%s, %s, %s, %s, %s) RETURNING id""",
                                    ('', user2_id, '14', '01', ''))
        date_of_b_id2 = db_connection.cur.fetchone()[0]

        current_date = '2025-12-20'

        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id1, current_timestamp='2024-01-01')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id1, current_timestamp='2024-01-14')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id1, current_timestamp='2024-12-20')

        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id2,current_timestamp='2024-01-01')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id2,current_timestamp='2024-01-14')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id2,current_timestamp='2024-12-20')

        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 0, current_date)
        assert 10001 not in res
        res = await get_none_notified_birthdate_in_interval(db_connection, 4, 7, current_date)
        assert 10001 not in res
        res = await get_none_notified_birthdate_in_interval(db_connection, 15, 30, current_date)
        assert len(res[10001]) == 1
        assert len(res.keys()) == 2

    @pytest.mark.asyncio
    # ДР в периоде, есть уведомления в периоде
    async def test_birth_in_interval_and_have_notif_not_in_interval(self, db_connection: DBService, clean_db):
        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10001,))
        user1_id: int = db_connection.cur.fetchone()[0]
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                                values (%s, %s, %s, %s, %s) RETURNING id""",
                                    ('', user1_id, '14', '01', ''))
        date_of_b_id1 = db_connection.cur.fetchone()[0]

        current_date = '2025-12-30'

        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id1,
                                current_timestamp='2024-01-14')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id1,
                                current_timestamp='2025-01-14')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id1,
                                current_timestamp='2025-12-25') # уведмоление за 20 дней до др

        res = await get_none_notified_birthdate_in_interval(db_connection, 0, 0, current_date)
        assert 10001 not in res
        res = await get_none_notified_birthdate_in_interval(db_connection, 4, 7, current_date)
        assert 10001 not in res
        res = await get_none_notified_birthdate_in_interval(db_connection, 15, 20, current_date)  # если до др 15-20 дней и в этот же период уже было уведомление, то не получать дату ДО
        assert 10001 not in res
        res = await get_none_notified_birthdate_in_interval(db_connection, 15, 18, current_date) # если до др 15-18 дней и в этот же период еще не было уведомлений, то получить дату ДР
        assert 10001 in res

    @pytest.mark.asyncio
    async def test_get_missed_births(self, db_connection: DBService, clean_db):
        db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10001,))
        user1_id: int = db_connection.cur.fetchone()[0]

        last_launch_date = '2024-03-22'
        db_connection.execute_query("""insert into execution_logs ("date") values (%s::date);""", (last_launch_date,))

        current_date = '2025-02-22'

        # 4 ДР после последнего запуска и 1 ДР после текущего запуска/в день запуска
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                                        values (%s, %s, %s, %s, %s) RETURNING id""",
                                    ('', user1_id, '23', '01', ''))
        date_of_b_id1 = db_connection.cur.fetchone()[0]

        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                                                values (%s, %s, %s, %s, %s) RETURNING id""",
                                    ('', user1_id, '10', '02', ''))
        date_of_b_id2 = db_connection.cur.fetchone()[0]

        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                                                        values (%s, %s, %s, %s, %s) RETURNING id""",
                                    ('', user1_id, '17', '02', ''))

        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                                                                values (%s, %s, %s, %s, %s) RETURNING id""",
                                    ('', user1_id, '25', '02', ''))
        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                                                                        values (%s, %s, %s, %s, %s) RETURNING id""",
                                    ('', user1_id, '11', '08', ''))

        db_connection.execute_query("""insert into date_of_births (celebrant_name, user_id, day, month, year) 
                                                                                                                values (%s, %s, %s, %s, %s) RETURNING id""",
                                    ('', user1_id, '23', '02', ''))

        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id1,
                                current_timestamp='2024-01-23')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id1,
                                current_timestamp='2025-01-22')

        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id2,
                                current_timestamp='2024-02-10')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id2,
                                current_timestamp='2024-02-07')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id2,
                                current_timestamp='2024-02-01')
        await save_notification(db_instance=db_connection, date_of_birth_id=date_of_b_id2,
                                current_timestamp='2023-02-10')


        res = await get_missed_births(db_instance=db_connection, current_date=current_date)
        assert len(res[10001]) == 4




# get_births_by_chat_id +
# check_is_user_own_row +
# get_rows_the_next_n_days +
# get_none_notified_birthdate_in_interval +
# get_missed_births

# def add_user() -> int:
#     db_connection.execute_query("""insert into users (chat_id) values (%s) RETURNING id;""", (10001,))
#     user_id = db_connection.cur.fetchone()[0]
#
#     return user_id

def add_n_rows_to_user(n_rows: int, user_id: int, db_connection: DBService, current_date: str, offset: int = 0):
    t = []
    for i in range(0, n_rows):
        # date = datetime.now() + timedelta(days=i)
        date = datetime.strptime(current_date, '%Y-%m-%d') + timedelta(days=i+offset)
        t.append((f"celebrant {i}", user_id, f"{date.day:02d}", f"{date.month:02d}", 'NULL'))

    db_connection.execute_many("""insert into date_of_births (celebrant_name, user_id, day, month, year)
                       values (%s, %s, %s, %s, %s)""", t)

# def add_n_rows_to_user_with_notifications(n_rows: int, user_id: int, db_connection: DBService, current_date: str):




class TestUtils:
    def test_is_int(self):
        assert utils.is_int('1')
        assert utils.is_int(1)
        assert utils.is_int(2)
        assert utils.is_int(-3)

    def test_is_not_int(self):
        assert not utils.is_int(None)
        assert not utils.is_int({})
        assert not utils.is_int([])

    def test_is_valid_date(self):
        assert utils.is_valid_date('13.05')
        assert utils.is_valid_date('15.06')
        assert utils.is_valid_date('15.06.2025')

    def test_is_invalid_date(self):
        assert not utils.is_valid_date('32.05')
        assert not utils.is_valid_date('sdfsd12')
        assert not utils.is_valid_date('    ')
        assert not utils.is_valid_date('12.06.999')
        assert not utils.is_valid_date('15.06.10000')

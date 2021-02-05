
import sqlite3
from config.config import db


class SqLite:
    def __init__(self):
        self.conn = sqlite3.connect(db, check_same_thread=False)
        self.conn.row_factory = self.dict_factory
        self.cursor = self.conn.cursor()
        self.create_base_table()

    def execute(self, sql):
        i = 3
        while i > 0:
            i -= 1
            try:
                self.cursor.execute(sql)
                self.conn.commit()
                return self.cursor
                # break
            except Exception as e:
                print(e)

    def create_base_table(self):
        # create save token table
        token_sql = "CREATE TABLE IF NOT EXISTS token (" \
                    "id INTEGER PRIMARY KEY AUTOINCREMENT," \
                    "ak varchar(128) NOT NULL," \
                    "sk varchar(128) NOT NULL," \
                    "access_token varchar(256) NOT NULL)"

        self.execute(sql=token_sql)

        # create dir table
        dir_sql = "CREATE TABLE IF NOT EXISTS dir (" \
                  "id INTEGER PRIMARY KEY AUTOINCREMENT," \
                  "dirname varchar(512) NOT NULL)"

        self.execute(sql=dir_sql)

        # create labeled data md5 table
        diff_sql = "CREATE TABLE IF NOT EXISTS diff (" \
                   "dir_id int(11) NOT NULL, " \
                   "md5 varchar(128) NOT NULL)"

        self.execute(sql=diff_sql)

    def close(self):
        self.cursor.close()
        self.conn.close()

    @staticmethod
    def dict_factory(c, row):
        d = {}
        for idx, col in enumerate(c.description):
            d[col[0]] = row[idx]
        return d


# s = SqLite()
# s.create_base_table()
# s.close()

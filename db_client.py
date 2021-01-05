################################################################################
"""
@Time    : 2020/12/19
@File    : db_client.py
@Author  : cenquanyu@baidu.com
"""
import logging
import pymysql
import log


class DbClient(object):
    """DB操作类
    """
    def __init__(self, user, passwd):
        self.dbname = 'iaas_op_data'
        self.dbhost = '10.21.225.21'
        self.db = pymysql.connect(self.dbhost, user, passwd, self.dbname, charset='utf8')
        self.cursor = self.db.cursor()

    def execute_sql(self, sql):
        """在db连接上执行sql语句"""
        self.cursor.execute(sql)

    def execute_sql_fetchall(self, sql):
        """在db连接上执行sql语句, 并返回结果"""
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def execute_sql_fetchall_dictlist(self, sql):
        """在db连接上执行sql语句, 并返回dictlist"""
        with self.db.cursor(cursor=pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def insert_all(self, table, *args, **kwargs):
        """插入数据"""
        data_dict = kwargs
        length = 0
        ksql, vsql = '', ''
        for k, v in data_dict:
            if length == 0:
                ksql = "INSERT INTO " + table + "(" + k
                vsql = "VALUES (" + v
            else:
                ksql += ',' + k
                vsql += ',' + v
            length += 1
        ksql += ")"
        vsql += ")"
        sql = ksql + vsql
        try:
            self.db.ping(reconnect=True)
            self.execute_sql(sql)
            self.db.commit()
            logging.info('Insert data \n')
            logging.info(data_dict)
            logging.info('---- Data Insert success ----')
        except Exception as e:
            logging.error(e)
            self.db.rollback()
            self.db.close()

    def insert(self, sql):
        """插入数据(使用sql)"""
        try:
            self.db.ping(reconnect=True)
            self.execute_sql(sql)
            self.db.commit()
        except Exception as e:
            logging.error(e)
            self.db.rollback()
            self.db.close()

    def update(self, sql):
        """更新数据(使用sql)"""
        try:
            self.db.ping(reconnect=True)
            self.execute_sql(sql)
            self.db.commit()
        except Exception as e:
            logging.error(e)
            self.db.rollback()
            self.db.close()

    def query_all(self, sql):
        """查询数据(返回元组)"""
        squery = ''
        try:
            self.db.ping(reconnect=True)
            squery = self.execute_sql_fetchall(sql)
        except Exception as e:
            logging.error(e)
            self.db.close()

        return squery

    def query_dictlist(self, sql):
        """查询数据(返回字典列表)"""
        squery = ''
        try:
            self.db.ping(reconnect=True)
            squery = self.execute_sql_fetchall_dictlist(sql)
        except Exception as e:
            logging.error(e)
            self.db.close()

        return squery
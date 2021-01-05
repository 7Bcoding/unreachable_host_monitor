################################################################################
"""
@Time    : 2020/12/19
@File    : alarm_callback_handler.py
@Author  : cenquanyu@baidu.com
"""
################################################################################

import logging
from queue import Queue

from alarm_callback_thread import AlarmCallbackThread
from iaas_op_tools.iaas_op_glue import hi_robot
from unreachable_data import *


class AlarmCallbackHandler(object):

    def __init__(self, thread_num, interval=1, times=3, timeout=3):
        self.thread_num = thread_num
        self.unreachable_queue = Queue()
        self.recover_queue = Queue()
        self.unreachable_host_dict = dict()  # 宕机机器
        self.recover_host_dict = dict()      # 恢复机器
        self.interval = interval             # ping的时间间隔
        self.times = times                   # ping的次数
        self.timeout = timeout               # telnet超时时间

    def get_unreachable_host_list(self):
        """获取宕机机器
        """
        db_conn = self.init_db_conn('iaas_op_data_ro', 'Baidu!@#321')
        sql = "SELECT * FROM bns_serviceunit_hostinfo WHERE product = 'BBC_SNIC_ONLINE'"
        host_dictlist = db_conn.query_dictlist(sql)
        logging.info('---------ONLINE_HOSTLIST---------:\n')
        logging.info(host_dictlist)

        for snic_host_dict in host_dictlist:
            self.unreachable_queue.put(snic_host_dict['ip'])
            self.unreachable_host_dict[snic_host_dict['ip']] = snic_host_dict['hostname']

        return host_dictlist

    def start_callback_work(self):
        """开启报警回调工作(多线程并发ping/telnet)
        """
        self.get_unreachable_host_list()
        thread_list = []
        for i in range(self.thread_num):
            thread = AlarmCallbackThread(self.unreachable_queue, self.unreachable_host_dict, self.interval, self.times,
                                       self.timeout)
            thread_list.append(thread)
            logging.info("%s start..." % thread.name)
            thread.start()
        for thread in thread_list:
            thread.join()
            logging.info("thread %s work is done " % thread.name)
        self.unreachable_queue.join()
        logging.info('---自动重启后恢复的机器列表---:\n %s' % UnreachableHostData.recover_dictlist)

        recover_hostlist = []
        recover_host_dictlist = []
        msg_list = []

        for recover_host in UnreachableHostData.recover_dictlist:
            recover_hostlist.append(recover_host['hostname'])
            msg_list.append("机器: %s, 宕机时间: %s, 恢复时间: %s " % (recover_host["hostname"],
                                                                         recover_host["unreachable_time"],
                                                                         recover_host["recover_time"]))
            recover_host_dictlist.append(recover_host)

        if len(msg_list) > 0:
            hi_message = "BBC智能卡恢复情况通报:\n" + '\n'.join(msg_list)
            hi_robot.send_hi_message_to_opgroup(hi_message, '2949052')


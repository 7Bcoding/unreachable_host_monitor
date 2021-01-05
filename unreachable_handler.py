################################################################################
"""
@Time    : 2020/12/19
@File    : unreachable_handler.py
@Author  : cenquanyu@baidu.com
"""
################################################################################

import logging
from datetime import datetime
from queue import Queue
from db_client import DbClient
from iaas_op_tools.iaas_op_glue import hi_robot
from iaas_op_tools.iaas_op_glue import nova_master_client
from iaas_op_tools.iaas_op_glue.argus_client import ArgusBlockAPIClient
from recover_thread import RecoverThread
from unreachable_data import *
from unreachable_thread import UnreachableThread


class UnreachableHandler(object):

    def __init__(self, thread_num, interval=1, times=3, timeout=3):
        self.thread_num = thread_num
        self.unreachable_queue = Queue()
        self.recover_queue = Queue()
        self.unreachable_host_dict = dict()  # 宕机机器
        self.recover_host_dict = dict()  # 恢复机器
        self.interval = interval  # ping的时间间隔
        self.times = times  # ping的次数
        self.timeout = timeout  # telnet超时时间

    def init_db_conn(self, user, passwd):
        try:
            db_conn = DbClient(user, passwd)
        except Exception as e:
            db_conn = None
            logging.exception("Database connection to %s init failed, please check: %s", 'username', e)
            raise e
        if not db_conn:
            logging.info("Database connection to %s init failed, stop task.", 'username')
            raise Exception("Database connection initialization failed.")
        logging.info("Database connection initialized: %s", 'username')
        return db_conn

    def get_recover_host_list(self):
        """获取宕机机器
        """
        db_conn = self.init_db_conn('username', 'password')
        sql = "SELECT * FROM unreachable_host_data WHERE ping_stat='False' OR telnet_stat='False'"
        host_dictlist = db_conn.query_dictlist(sql)
        logging.info('---------ONLINE_UNREACHABLE_HOSTLIST---------:\n')
        logging.info(host_dictlist)

        for snic_host_dict in host_dictlist:
            self.recover_queue.put(snic_host_dict['ip'])
            unreachable_time = snic_host_dict['unreachable_time'].strftime("%Y-%m-%d %H:%M:%S")
            self.recover_host_dict[snic_host_dict['ip']] = {'hostname': snic_host_dict['hostname'],
                                                            'unreachable_time': unreachable_time}

    def update_recover_host_info(self):
        """更新机器恢复信息
        """
        db_conn = self.init_db_conn('username', 'password')
        recover_host_dictlist = UnreachableHostData.recover_dictlist
        logging.info('更新恢复的机器: %s' % recover_host_dictlist)
        for recover_host in recover_host_dictlist:
            sql = "UPDATE unreachable_host_data SET recover_time='%s',ping_stat='True',telnet_stat='True' WHERE hostname='%s'" % \
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), recover_host['hostname'])

            db_conn.update(sql)

    def get_unreachable_host_list(self):
        """获取在线机器
        """
        db_conn = self.init_db_conn('username', 'password')
        sql = "SELECT * FROM bns_serviceunit_hostinfo WHERE product = 'BBC_SNIC_ONLINE'"
        host_dictlist = db_conn.query_dictlist(sql)

        for snic_host_dict in host_dictlist:
            self.unreachable_queue.put(snic_host_dict['ip'])
            self.unreachable_host_dict[snic_host_dict['ip']] = snic_host_dict['hostname']

    def update_unreachable_host_info(self, final_host_dictlist):
        """更新机器宕机信息
        """
        db_conn = self.init_db_conn('username', 'password')
        unreachable_host_dictlist = final_host_dictlist
        for host in unreachable_host_dictlist:
            sql = "INSERT INTO unreachable_host_data" \
                  " (hostname, ip, ping_stat, telnet_stat, unreachable_time, recover_time) " \
                  "VALUES ('%s','%s','%s','%s','%s','%s') on duplicate key update " \
                  "hostname='%s', ip='%s', ping_stat='%s', telnet_stat='%s', unreachable_time='%s', recover_time='%s'" % \
                  (host['hostname'], host['ip'], host['ping_stat'],
                   host['telnet_stat'], host['unreachable_time'], host['recover_time'],
                   host['hostname'], host['ip'], host['ping_stat'],
                   host['telnet_stat'], host['unreachable_time'], host['recover_time'])
            # sql = "INSERT INTO unreachable_host_data" \
            #       " (hostname, ip, ping_stat, telnet_stat, unreachable_time, recover_time) " \
            #       "VALUES ('%s','%s','%s','%s','%s','%s')" % \
            #       (host['hostname'], host['ip'], host['ping_stat'],
            #        host['telnet_stat'], host['unreachable_time'], host['recover_time'])

            # sql = "INSERT INTO unreachable_host_data" \
            #       " (hostname, ip, ping_stat, telnet_stat, unreachable_time, recover_time) " \
            #       "VALUES ('%s','%s','%s','%s','%s','%s') WHERE NOT EXSISTS (select '%s','%s','%s','%s','%s','%s'" \
            #       " from unreachable_host_data WHERE hostname='%s')" % \
            #       (host['hostname'], host['ip'], host['ping_stat'],host['telnet_stat'],
            #        host['unreachable_time'], host['recover_time'], host['hostname'],
            #        host['ip'], host['ping_stat'],host['telnet_stat'], host['unreachable_time'],
            #        host['recover_time'], host['hostname'])

            recover_time = datetime.strptime(host['recover_time'], '%Y-%m-%d %H:%M:%S')
            unreachable_time = datetime.strptime(host['unreachable_time'], '%Y-%m-%d %H:%M:%S')
            if (recover_time - unreachable_time).seconds >= 300:
                db_conn.insert(sql)

    def start_recover_check_work(self):
        """开启宕机恢复检测工作
        """
        self.get_recover_host_list()
        thread_list = []
        logging.info('recover_queue_size: %d' % self.recover_queue.qsize())
        for i in range(self.recover_queue.qsize()):
            thread = RecoverThread(self.recover_queue, self.recover_host_dict, self.interval, self.times, self.timeout)
            thread_list.append(thread)
            logging.info("%s start..." % thread.name)
            thread.start()
        for thread in thread_list:
            thread.join()
            logging.info("thread %s work is done " % thread.name)
        self.unreachable_queue.join()
        self.update_recover_host_info()
        logging.info("snic bbc ip queue check work is all done")
        logging.info('ping success list: %s, num: %d' % (UnreachablePingData.ping_success_list,
                                                         len(UnreachablePingData.ping_success_list)))
        logging.info('telnet success list: %s, num: %d' % (UnreachableTelnetData.telnet_success_list,
                                                           len(UnreachableTelnetData.telnet_success_list)))
        logging.info("recover host: %s, num: %d" % (UnreachableHostData.recover_list,
                                                    UnreachableHostData.recover_num))

    def start_unreachable_check_work(self):
        """开启宕机检测工作(多线程并发ping/telnet)
        """
        self.get_unreachable_host_list()
        thread_list = []
        for i in range(self.thread_num):
            thread = UnreachableThread(self.unreachable_queue, self.unreachable_host_dict, self.interval, self.times,
                                       self.timeout)
            thread_list.append(thread)
            logging.info("%s start..." % thread.name)
            thread.start()
        for thread in thread_list:
            thread.join()
            logging.info("thread %s work is done " % thread.name)
        self.unreachable_queue.join()

        logging.info("snic bbc ip queue check work is all done")
        logging.info('ping failed list: %s, num: %d' % (UnreachablePingData.ping_failed_list,
                                                        len(UnreachablePingData.ping_failed_list)))
        logging.info('telnet failed list: %s, num: %d' % (UnreachableTelnetData.telnet_failed_list,
                                                          len(UnreachableTelnetData.telnet_failed_list)))
        logging.info("unreachable host: %s, num: %d" % (UnreachableHostData.unreachhost_dictlist,
                                                        len(UnreachableHostData.unreachhost_dictlist)))

        argus_client = ArgusBlockAPIClient()
        final_hostlist = []
        final_host_dictlist = []
        msg_list = []
        # 剔除不满足条件的host
        for unreachable_host in UnreachableHostData.unreachhost_dictlist:
            block_info = argus_client.get_block_status_by_name(unreachable_host['hostname'])
            logging.info('---- block_status ----%s' % block_info['block'])
            # 告警屏蔽的机器剔除掉
            if block_info['block'] == 0:
                novamaster_client = nova_master_client.create_by_hostname(unreachable_host['hostname'])
                vm_list = novamaster_client.GetVMUUIDListByHost(unreachable_host['hostname'])
                logging.info('-----------vm_list--------: %s' % vm_list)
                if len(vm_list) > 0:
                    vm_state = novamaster_client.get_vm_state(vm_list[0])
                    logging.info('-----------vm_list--------: %s' % vm_state)
                    # 获取实例状态，stop的剔除掉
                    if vm_state == 'active':
                        final_hostlist.append(unreachable_host['hostname'])
                        msg_list.append("机器: %s, 宕机时间: %s, 恢复时间: %s " % (unreachable_host["hostname"],
                                                                         unreachable_host["unreachable_time"],
                                                                         unreachable_host["recover_time"]))
                        final_host_dictlist.append(unreachable_host)

        print('unreachable_host: %s' % ','.join(final_hostlist))

        if len(msg_list) > 0:
            hi_message = "宕机情况通报:\n" + '\n'.join(msg_list)
            hi_robot.send_hi_message_to_opgroup(hi_message, '2949052')

        msg_list = []
        for recover_host in UnreachableHostData.recover_dictlist:
            msg_list.append("机器: %s, 宕机时间: %s, 恢复时间: %s " % (recover_host["hostname"],
                                                             recover_host["unreachable_time"],
                                                             recover_host["recover_time"]))
        if len(msg_list) > 0:
            hi_message = "恢复情况通报:\n" + '\n'.join(msg_list)
            hi_robot.send_hi_message_to_opgroup(hi_message, '2949052')

        # 更新宕机信息
        self.update_unreachable_host_info(final_host_dictlist)

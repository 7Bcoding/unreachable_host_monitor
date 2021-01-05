################################################################################
"""
@Time    : 2020/12/19
@File    : recover_thread.py
@Author  : cenquanyu@baidu.com
"""
################################################################################
import logging
import re
import subprocess
from datetime import datetime
import telnetlib
import threading
from unreachable_data import *


class RecoverThread(threading.Thread):
    """宕机恢复检测线程
    """

    def __init__(self, ip_queue, host_dict, interval, times, timeout):
        threading.Thread.__init__(self)
        self.ip_queue = ip_queue
        self.host_dict = host_dict
        self.interval = interval
        self.times = times
        self.timeout = timeout
        self.lock = threading.Lock()

    def run(self):
        """线程任务
        """
        while True:
            try:
                host_ip = self.ip_queue.get(block=True, timeout=3)
            except Exception as e:
                logging.error('Can not finish the task. job done. %s' % e)
                break
            logging.info(host_ip)
            ping_status = self.ping_ipaddr(host_ip)
            telnet_status = self.telnet_addr(host_ip, 22, self.timeout)
            logging.info('机器状态: %s, %s, %s' % (host_ip, str(ping_status), str(telnet_status)))
            if ping_status and telnet_status:
                self.lock.acquire()
                UnreachableHostData.recover_num += 1
                if self.host_dict[host_ip]['hostname'] not in UnreachableHostData.recover_set:
                    UnreachableHostData.recover_set.add(self.host_dict[host_ip]['hostname'])
                    UnreachableHostData.recover_list.append(self.host_dict[host_ip]['hostname'])
                    UnreachableHostData.recover_dictlist.append({
                        'hostname': self.host_dict[host_ip]['hostname'], 'ip': host_ip,
                        'ping_stat': str(ping_status), 'telnet_stat': str(telnet_status),
                        'unreachable_time': self.host_dict[host_ip]['unreachable_time'],
                        'recover_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    logging.info('恢复的机器信息: %s' % UnreachableHostData.recover_dictlist)

                self.lock.release()
            self.ip_queue.task_done()

    def ping_ipaddr(self, ip_addr):
        """ ping检测
        """
        output = None
        try:
            p = subprocess.Popen("ping -c {0} {1} \n".format(self.times, ip_addr),
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
            output = p.stdout.read().decode('gbk')
        except Exception as e:
            logging.error('ping process error: %s' % e)

        ping_status = True
        regIP = r'\d+\.\d+\.\d+\.\d+'
        regRecv = r', (\d.*?) received'
        regLost = r', (\d.*?%) packet loss'
        regAverage = r'= (.*?) ms'
        ip = re.search(regIP, output)
        lost = re.findall(regLost, output)[0]
        received = re.findall(regRecv, output)[0]
        if int(received) == 0:
            ping_status = False
            logging.info('--------ping failed:------%s' % ip_addr)
        else:
            self.lock.acquire()
            if self.host_dict[ip_addr]['hostname'] not in UnreachablePingData.ping_success_set:
                UnreachablePingData.ping_success_set.add(self.host_dict[ip_addr]['hostname'])
                UnreachablePingData.ping_success_list.append(self.host_dict[ip_addr]['hostname'])
            self.lock.release()
            logging.info('--------ping ok:------%s' % ip_addr)

        return ping_status

    def telnet_addr(self, ip_addr, port, timeout):
        """ telnet检测
        """
        try:
            tn = telnetlib.Telnet()
            tn.open(ip_addr, port, timeout)
            self.lock.acquire()
            if self.host_dict[ip_addr]['hostname'] not in UnreachableTelnetData.telnet_success_set:
                UnreachableTelnetData.telnet_success_set.add(self.host_dict[ip_addr]['hostname'])
                UnreachableTelnetData.telnet_success_list.append(self.host_dict[ip_addr]['hostname'])
                logging.info("--------telnet success ip:------%s" % ip_addr)
            self.lock.release()
        except Exception as e:
            logging.error('telnet process error: %s' % e)
            return False
        return True

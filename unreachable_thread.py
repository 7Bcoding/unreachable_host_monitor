################################################################################
"""
@Time    : 2020/12/19
@File    : unreachable_thread.py
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


class UnreachableThread(threading.Thread):
    """BBC智能卡宕机检测线程
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
            self.ip_queue.task_done()
            ping_status = self.ping_ipaddr(host_ip)
            telnet_status = self.telnet_addr(host_ip, 22, self.timeout)
            # logging.info('telnet failed host: %s %s' % (host_ip, telnet_status))
            if (ping_status is False) or (telnet_status is False):
                self.lock.acquire()
                UnreachableHostData.unreachable_num += 1
                if self.host_dict[host_ip] not in UnreachableHostData.unreachhost_set:
                    UnreachableHostData.unreachhost_set.add(self.host_dict[host_ip])
                    UnreachableHostData.unreachhost_list.append(self.host_dict[host_ip])
                    UnreachableHostData.unreachhost_dictlist.append({
                        'hostname': self.host_dict[host_ip], 'ip': host_ip,
                        'ping_stat': str(ping_status), 'telnet_stat': str(telnet_status),
                        'unreachable_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'recover_time': ' '})
                self.lock.release()

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
            self.lock.acquire()
            if self.host_dict[ip_addr] not in UnreachablePingData.ping_failed_set:
                UnreachablePingData.ping_failed_set.add(self.host_dict[ip_addr])
                UnreachablePingData.ping_failed_list.append(self.host_dict[ip_addr])
            self.lock.release()
            # logging.info('--------ping failed:------%s' % ip_addr)
        # else:
        #     # logging.info('--------ping ok:------%s' % ip_addr)

        return ping_status

    def telnet_addr(self, ip_addr, port, timeout):
        """ telnet检测
        """
        try:
            tn = telnetlib.Telnet()
            tn.open(ip_addr, port, timeout)
        except Exception as e:
            logging.error('telnet process error: %s' % e)
            self.lock.acquire()
            if self.host_dict[ip_addr] not in UnreachableTelnetData.telnet_failed_set:
                UnreachableTelnetData.telnet_failed_set.add(self.host_dict[ip_addr])
                UnreachableTelnetData.telnet_failed_list.append(self.host_dict[ip_addr])
                # logging.info("--------telnet failed ip:------%s" % ip_addr)
            self.lock.release()
            return False
        return True


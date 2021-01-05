################################################################################
"""
@Time    : 2020/12/19
@File    : alarm_callback_thread.py
@Author  : cenquanyu@baidu.com
"""
################################################################################
import logging
import re
import subprocess
from datetime import datetime
import time
import telnetlib
import threading
from unreachable_data import *


def retry(max_retry):
    """ 自定义重试装饰器
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retry_times = 0
            while retry_times < max_retry:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retry_times += 1
                    time.sleep(3)
                    logging.error('Reboot Error %s' % e)
            else:
                raise TypeError
        return wrapper
    return decorator


class AlarmCallbackThread(threading.Thread):
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
            if (ping_status is False) or (telnet_status is False):
                logging.info('开始自动重启工作......')
                if self.reboot(host_ip):
                    self.lock.acquire()
                    UnreachableHostData.recover_num += 1
                    if self.host_dict[host_ip] not in UnreachableHostData.recover_set:
                        UnreachableHostData.recover_set.add(self.host_dict[host_ip])
                        UnreachableHostData.recover_list.append(self.host_dict[host_ip])
                        UnreachableHostData.recover_dictlist.append({
                            'hostname': self.host_dict[host_ip], 'ip': host_ip,
                            'ping_stat': str(ping_status), 'telnet_stat': str(telnet_status),
                            'unreachable_time': self.host_dict[host_ip]['unreachable_time'],
                            'recover_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                        logging.info('恢复的机器信息: %s' % UnreachableHostData.recover_dictlist)
                    self.lock.release()

    def ping_ipaddr(self, ip_addr, times):
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
            self.lock.release()
            return False
        return True

    @retry(max_retry=2)
    def reboot(self, ip_addr):
        """ 重启机器
        """
        try:
            p = subprocess.Popen("reboot \n".format(self.times, ip_addr),
                                 stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
            output = p.stdout.read().decode('utf-8')
        except Exception as e:
            logging.error('reboot process error: %s' % e)

        ping_status = False
        telnet_status = False
        org_time = time.time()
        while (time.time() - org_time) < 300 and (ping_status is False or telnet_status is False):
            ping_status = self.ping_ipaddr(ip_addr)
            telnet_status = self.telnet_addr(ip_addr, 22, 10)
            logging.info('wait till reboot work finish...')

        if ping_status and telnet_status:
            return True
        else:
            raise RebootTimeoutError('reboot timeout, try again...')


class RebootTimeoutError(Exception):
    pass


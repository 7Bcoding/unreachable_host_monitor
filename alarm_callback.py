################################################################################
"""
@Time    : 2020/12/19
@File    : alarm_callback.py
@Author  : cenquanyu@baidu.com
"""
################################################################################

import time
import log
from alarm_callback_handler import AlarmCallbackHandler
from unreachable_handler import UnreachableHandler


def main():
    log.init_log('./log/snic_bbc_unreachable')
    alarm_callback_handler = AlarmCallbackHandler(250, 1, 3, 10)
    start_time = time.time()
    alarm_callback_handler.start_callback_work()
    end_time = time.time()
    print('callback action use time: %d' % (end_time - start_time))


if __name__ == '__main__':
    main()

################################################################################
"""
@Time    : 2020/12/19
@File    : snic_bbc_unreachable_monitor.py
@Author  : cenquanyu@baidu.com
"""
################################################################################

import time
import log
from unreachable_handler import UnreachableHandler


def main():
    log.init_log('./log/snic_bbc_unreachable')
    unreachable_handler = UnreachableHandler(250, 1, 3, 10)
    start_time = time.time()
    unreachable_handler.start_recover_check_work()
    unreachable_handler.start_unreachable_check_work()
    end_time = time.time()
    print('unreachable_time: %d' % (end_time - start_time))


if __name__ == '__main__':
    main()

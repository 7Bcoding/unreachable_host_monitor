################################################################################
"""
@Time    : 2020/12/19
@File    : unreachable_data.py
@Author  : cenquanyu@baidu.com
"""
################################################################################


class UnreachableHostData(object):
    unreachable_num = 0
    recover_num = 0
    unreachhost_set = set()
    unreachhost_list = []
    unreachhost_dictlist = []
    recover_set = set()
    recover_list = []
    recover_dictlist = []


class UnreachablePingData(object):
    ping_failed_set = set()
    ping_failed_list = []
    ping_success_set = set()
    ping_success_list = []


class UnreachableTelnetData(object):
    telnet_failed_set = set()
    telnet_failed_list = []
    telnet_success_set = set()
    telnet_success_list = []
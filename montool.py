################################################################################
"""
@Time    : 2020/12/19
@File    : montool.py
@Author  : cenquanyu@baidu.com
"""
################################################################################

import time
import logging
from datetime import datetime

from http_client import HTTPClient

ARCHER_TOKEN = "W0o32Fd7JUqrQhURkT6K8cNVi2lXmfIw"
GET_BLOCK_TIMEOUT = 5


class ArgusClient(object):
    """
        block argus
    """

    def __init__(self, namespace, dimension=None):
        """
        make block less
        Args:
            namespace: Machine or BNS
        """
        self.name = namespace
        self._status = None
        self._expired = None
        self.dimension = dimension

    @property
    def status(self):
        self._get_block_status()
        return self._status

    @property
    def expired(self):
        self._get_block_status()
        return self._expired

    def block(self, hours=4, hostname=None):
        """屏蔽机器
        """
        if hostname is not None:
            self.name = hostname

        logging.info("Start to block %s" % (self.name))
        block_time = time.strftime('%Y-%m-%d %X',
                                   time.localtime(hours * 3600 +
                                                  time.time()))

        logging.info("Try to block %s to %s" % (self.name, block_time))
        url = "http://mt.noah.baidu.com/block/index.php?r=BlockService/blockAll"
        params = {
            'info': self.dimension and self.name + ":" + self.dimension or self.name,
            'token': ARCHER_TOKEN,
            'disableTime': block_time,
            'comment': '[MTool]',
            'tags': ' '
        }
        logging.info("Block %s url = %s, params = %s" % (self.name, url, params))

        response_json = HTTPClient.http_get_json(url, params)

        logging.info("Block %s res: %s" % (self.name, response_json))
        time.sleep(1)

        # 请求正确
        if response_json is not None and response_json['success'] is True:
            expired_time = self.expired
            if not expired_time:
                logging.debug("get host %s expired time fail" % self.name)
                return False
            delta_hour = (expired_time - datetime.now()).total_seconds() / 3600
            logging.info("%s delta_hour is %s" % (self.name, delta_hour))
            if delta_hour < 24:
                logging.info("%s delta_hour is error: %s" % (self.name, delta_hour))
                return False

            logging.info("%s blocked for %s hours, expect %s hours" % (self.name, delta_hour, hours))
            # if self.status and abs(delta_hour - hours) < 1:
            if self.status and delta_hour >= hours - 1:
                logging.info("%s block succeed" % self.name)
                return True

            # 不行? 重试一次
            # logging.info("%s block FAILED, retry" % self.name)
            # return self.block(hours)

        return False

    def unblock(self, hostname=None):
        """
        解除屏蔽报警
        Returns:True
        """
        if hostname is not None:
            self.name = hostname

        url = "http://mt.noah.baidu.com/block/index.php?r=BlockService/unblockAll"
        params = {
            'info': self.dimension and self.name + ":" + self.dimension or self.name,
            'token': ARCHER_TOKEN,
            'comment': '[MTool]',
            'tags': ' '
        }
        response_json = HTTPClient.http_get_json(url, params)
        if response_json is not None and response_json.get('success') is True:
            return True
        return False

    def _get_block_status(self):
        """
        sample request content:
        {
            "data": {
                "block": 1,
                "blockType": "3",
                "dimension": "cq02-bcc-online-com033.cq02",
                "disableTime": "2016-09-26 15:44:46",
                "name": "cq02-bcc-online-com033.cq02",
                "startTime": null
            },
            "message": "ok",
            "success": true
        }
        or:
        {
            "data": {
                "block": 0,
                "blockType": null,
                "dimension": null,
                "disableTime": null,
                "name": "cq02-bcc-online-com053.cq02",
                "startTime": null
            },
            "message": "ok",
            "success": true
        }
        Returns:
        """
        url = "http://mt.noah.baidu.com/block/index.php?r=BlockService/getblockstatus"
        data = {"name": self.dimension and self.name + ":" + self.dimension or self.name}
        response_json = HTTPClient.http_get_json(url=url, params=data)
        logging.info("%s get_block_state , res: %s" % (self.name, response_json))

        if response_json is not None and response_json.get('success') is True:
            status_json = response_json.get('data')
            self._status = bool(int(status_json['block']))
            self.type = status_json['blockType']
            self._expired = self._status and datetime.strptime(status_json['disableTime'],
                                                               '%Y-%m-%d %H:%M:%S') or None

            logging.info("%s expired at %s" % (self.name, self._expired))
            if self._expired:
                return

    # def _get_block_status(self):
    #     """
    #     sample request content:
    #     {
    #         "data": {
    #             "block": 1,
    #             "blockType": "3",
    #             "dimension": "cq02-bcc-online-com033.cq02",
    #             "disableTime": "2016-09-26 15:44:46",
    #             "name": "cq02-bcc-online-com033.cq02",
    #             "startTime": null
    #         },
    #         "message": "ok",
    #         "success": true
    #     }
    #     or:
    #     {
    #         "data": {
    #             "block": 0,
    #             "blockType": null,
    #             "dimension": null,
    #             "disableTime": null,
    #             "name": "cq02-bcc-online-com053.cq02",
    #             "startTime": null
    #         },
    #         "message": "ok",
    #         "success": true
    #     }
    #     Returns:
    #     """
    #     url = "http://mt.noah.baidu.com/block/index.php?r=BlockService/getblockstatus"
    #     data = {"name": self.dimension and self.name + ":" + self.dimension or self.name}
    #     start_time = int(time.time())
    #     retry = 1
    #
    #     while int(time.time()) <= (start_time + GET_BLOCK_TIMEOUT):
    #         logging.info("%s get_block_status: current is %s, wait until %s " % (self.name,
    #                                                                              int(time.time()),
    #                                                                              start_time + GET_BLOCK_TIMEOUT))
    #         response_json = HTTPClient.http_get_json(url=url, params=data)
    #         logging.info("%s get_block_state for %s time, res: %s" % (self.name, retry, response_json))
    #
    #         if response_json is not None and response_json.get('success') is True:
    #             status_json = response_json.get('data')
    #             self._status = bool(int(status_json['block']))
    #             self.type = status_json['blockType']
    #             self._expired = self._status and datetime.strptime(status_json['disableTime'],
    #                                                                '%Y-%m-%d %H:%M:%S') or None
    #
    #             logging.info("%s expired at %s" % (self.name, self._expired))
    #             if self._expired:
    #                 return
    #
    #         time.sleep(10)
    #         retry += 1

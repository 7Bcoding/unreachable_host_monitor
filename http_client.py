################################################################################
"""
@Time    : 2020/12/19
@File    : http_client.py
@Author  : cenquanyu@baidu.com
"""
################################################################################

import json
import requests
import logging
from requests.exceptions import Timeout
from requests.exceptions import ConnectionError
from simplejson import JSONDecodeError


class HTTPClient(object):

    @staticmethod
    def http_get_json(url, params=None, headers=None, FOR_STATISTICS=False):
        # todo retry = 3
        """
        get json from http url
        Args:
            headers:
            url:
            params:

        Returns:
            json or None if any ERROR occurs
        """
        # logging.info("GET url=%s params=%s headers=%s" % (url, params, headers))
        if FOR_STATISTICS is True:
            logging.info("SLASH RUN API: GET url=%s params=%s headers=%s" % (url, params, headers))

        try:
            req = requests.get(url, params=params, timeout=10, headers=headers)
            if req.status_code != 200:
                return None
            response_json = req.json()
        except Timeout or ConnectionError:
            logging.error('HTTP Connection Reset or Timeout. url=%s params=%s', url, params)
        except ValueError:
            logging.error('No JSON object could be decoded ' + url)
        else:
            return response_json

    @staticmethod
    def http_post_json(url, json_dict, retry=3, einfo=None, FOR_STATISTICS=False):
        """

        Args:
            einfo: exception instance
            url: url
            json_dict: dict
            retry: int

        Returns:
            req.json()
        """
        if FOR_STATISTICS is True:
            logging.info("SLASH RUN API: POST url=%s params=%s" % (url, json_dict))

        if retry <= 0:
            logging.error("POST JSON error, max retry exceeded, url: %s, json: %s, retry:%d" % (
                url, json.dumps(json, ensure_ascii=False), retry - 1))
            if einfo and isinstance(einfo, Exception):
                raise einfo

        try:
            req = requests.post(url=url, data=json_dict)
            logging.info("http post json res = %s" % req.text)
            response_dict = req.json()
        except (requests.RequestException, JSONDecodeError, ValueError) as e:
            logging.error("POST JSON error , url: %s, json_dict: %s, retry:%d" % (
                url, json.dumps(json, ensure_ascii=False), retry - 1), einfo=e)
            return HTTPClient.http_post_json(url, json, retry=retry - 1)
        except Exception as e:
            logging.error(e)

        else:
            return response_dict

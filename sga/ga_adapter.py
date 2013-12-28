# -*- coding: utf-8 -*-

import logging
import json
import socket
import errno
import time
import re
import urlparse


class GAAdapter(object):
    _ga_id = None
    _ga_agent_host = None
    _ga_agent_port = None
    _ga_forbid_paths = None
    _ga_allow_paths = None
    _ga_logger_name = None

    _local_ip = ''

    _socket = None

    def __init__(self):
        self._local_ip = socket.gethostbyname(socket.gethostname()) or ''

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 非阻塞
        self._socket.setblocking(0)

    def __del__(self):
        if self._socket:
            self._socket.close()

    def send_data_to_ga_agent(self, send_dict):
        """
        可以在网站中调用
        """
        try:
            self._socket.sendto(json.dumps(send_dict), (self._ga_agent_host, self._ga_agent_port))
        except socket.error, e:
            # errno.EWOULDBLOCK = errno.EAGAIN = 11
            if e.args[0] == errno.EWOULDBLOCK:
                self.logger.info('errno.EWOULDBLOCK')
            else:
                self.logger.error('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())

    @property
    def logger(self):
        raise Exception('should override')

    def is_ga_request(self, path):
        """
        request是否要被统计
        """

        # 先判断是否在forbid列表里，只要发现就直接拒绝
        for pattern in self._ga_forbid_paths:
            if re.match(pattern, path):
                self.logger.debug('path is in forbid paths. patten: %s, path: %s', pattern, path)
                return False

        # 只有allow列表不为空的情况下，才有效
        if self._ga_allow_paths:
            for pattern in self._ga_allow_paths:
                if re.match(pattern, path):
                    return True
            else:
                self.logger.debug('path is not in allow paths. path: %s', path)
                return False

        return True

# -*- coding: utf-8 -*-
"""
要求配置:
    GA_ID : Google分析的跟踪ID
    GA_AGENT_HOST : GAAgent的启动IP
    GA_AGENT_PORT : GAAgent的启动端口
    GA_FORBID_PATHS : 被拒绝的paths，优先级高于 GA_ALLOW_PATHS
    GA_ALLOW_PATHS : 被允许的paths
    GA_HACK_PATHS: 上报时按照规则替换，在allow和forbid判断之后进行. 示例: [(r'^/all(\S+)', r'ok\g<1>')]
    GA_LOGGER_NAME : 用来打印log的name
"""

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
    _ga_hack_paths = None
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
        for pattern in self._ga_forbid_paths or tuple():
            if re.match(pattern, path):
                self.logger.debug('path is in forbid paths. patten: %s, path: %s', pattern, path)
                return False

        # 改成不为None就有效，这样空列表也是生效的
        if self._ga_allow_paths is not None:
            for pattern in self._ga_allow_paths:
                if re.match(pattern, path):
                    return True
            else:
                self.logger.debug('path is not in allow paths. path: %s', path)
                return False

        return True

    def hack_path(self, path):
        """
        将path替换为需要上报的
        """
        if not self._ga_hack_paths:
            return path

        for src_p, dst_p in self._ga_hack_paths:
            if not re.match(src_p, path):
                continue

            try:
                return re.sub(src_p, dst_p, path)
            except Exception, e:
                self.logger.error('re.sub fail. path: %s, src_p:%s, dst_p: %s, e: %s', path, src_p, dst_p, e)
                return path

        return path
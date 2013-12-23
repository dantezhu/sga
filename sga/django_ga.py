# -*- coding: utf-8 -*-

"""
django插件，绑定之后可以自动给本地的ga_agent发送数据
要求配置:
    GA_ID : Google分析的跟踪ID
    GA_AGENT_HOST : GAAgent的启动IP
    GA_AGENT_PORT : GAAgent的启动端口
    GA_FORBID_PATHS : 被拒绝的paths，优先级高于 GA_ALLOW_PATHS
    GA_ALLOW_PATHS : 被允许的paths
    GA_LOG_NAME : 用来打印log的name
"""

import logging
import socket
import json
import errno
import time
import re
import urlparse
from django.conf import settings

import constants


class DjangoGA(object):
    _ga_id = None
    _ga_agent_host = None
    _ga_agent_port = None
    _ga_forbid_paths = None
    _ga_allow_paths = None
    _ga_log_name = None

    _local_ip = ''

    _socket = None

    def __init__(self):
        self._ga_id = getattr(settings, 'GA_ID', None)
        self._ga_agent_host = getattr(settings, 'GA_AGENT_HOST', None) or constants.GA_AGENT_DEFAULT_HOST
        self._ga_agent_port = getattr(settings, 'GA_AGENT_PORT', None) or constants.GA_AGENT_DEFAULT_PORT
        self._ga_forbid_paths = getattr(settings, 'GA_FORBID_PATHS', None) or []
        self._ga_allow_paths = getattr(settings, 'GA_ALLOW_PATHS', None) or []
        self._ga_log_name = getattr(settings, 'GA_LOG_NAME', None)

        self._local_ip = socket.gethostbyname(socket.gethostname()) or ''

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 非阻塞
        self._socket.setblocking(0)

    def process_request(self, request):
        request.ga_begin_time = time.time()

    def process_response(self, request, response):
        """
        无论是否抛出异常，都会执行这一步
        """
        self._send_ga_data(request)
        return response

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
        return logging.getLogger(self._ga_log_name or 'django_ga')

    def _send_ga_data(self, request):
        self.logger.debug('ga_id:%s', self._ga_id)

        if not self._ga_id:
            return False

        if not self._is_ga_request(request):
            return False

        try:
            send_dict = self._gen_send_dict(request)
            if not send_dict:
                self.logger.debug('invalid request')
                return False
            self.send_data_to_ga_agent(send_dict)

            return True
        except Exception, e:
            self.logger.error('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())

        return False

    def _is_ga_request(self, request):
        """
        request是否要被统计
        """

        # 先判断是否在forbid列表里，只要发现就直接拒绝
        for pattern in self._ga_forbid_paths:
            if re.match(pattern, request.path):
                self.logger.debug('path is in forbid paths. patten: %s, path: %s', pattern, request.path)
                return False

        # 只有allow列表不为空的情况下，才有效
        if self._ga_allow_paths:
            for pattern in self._ga_allow_paths:
                if re.match(pattern, request.path):
                    return True
            else:
                self.logger.debug('path is not in allow paths. path: %s', request.path)
                return False

        return True

    def _gen_send_dict(self, request):
        """
        生成发送的dict
        """
        if not getattr(request, 'ga_begin_time', None):
            return None

        load_time = int((time.time()-request.ga_begin_time) * 1000)

        ga_referrer_path = ''
        if request.META.get('HTTP_REFERER', ''):
            try:
                parse_result = urlparse.urlparse(request.META['HTTP_REFERER'])
                ga_referrer_path = '/%s%s' % (parse_result.netloc, parse_result.path)
            except Exception, e:
                self.logger.info('urlparse fail. e: %s', e)

        send_dict = dict(
            funcname='track_pageview',
            tracker=dict(
                __ga=True,
                account_id=self._ga_id,
                domain_name=request.get_host(),
                campaign=dict(
                    __ga=True,
                    source=self._local_ip,
                    content=ga_referrer_path,
                ),
            ),
            session=dict(
                __ga=True,
            ),
            page=dict(
                __ga=True,
                path=request.path,
                load_time=load_time,
            ),
            visitor=dict(
                __ga=True,
                ip_address=request.META.get('REMOTE_ADDR', ''),
            ),
        )

        return send_dict

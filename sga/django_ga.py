# -*- coding: utf-8 -*-

"""
django插件，绑定之后可以自动给本地的ga_center发送数据
要求配置:
    GA_ID : Google分析的跟踪ID
    GA_CENTER_HOST : GACenter的启动IP
    GA_CENTER_PORT : GACenter的启动端口
    GA_FORBID_PATHS : 被拒绝的paths，优先级高于 GA_ALLOW_PATHS
    GA_ALLOW_PATHS : 被允许的paths
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

logger = logging.getLogger('django_ga')


class DjangoGA(object):
    _ga_id = None
    _ga_center_host = None
    _ga_center_port = None
    _ga_forbid_paths = None
    _ga_allow_paths = None

    _local_ip = ''

    _socket = None

    def __init__(self):
        self._ga_id = getattr(settings, 'GA_ID', None)
        self._ga_center_host = getattr(settings, 'GA_CENTER_HOST', None) or constants.GA_CENTER_DEFAULT_HOST
        self._ga_center_port = getattr(settings, 'GA_CENTER_PORT', None) or constants.GA_CENTER_DEFAULT_PORT
        self._ga_forbid_paths = getattr(settings, 'GA_FORBID_PATHS', None) or []
        self._ga_allow_paths = getattr(settings, 'GA_ALLOW_PATHS', None) or []

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

    def send_data_to_ga_center(self, send_dict):
        """
        可以在网站中调用
        """
        try:
            self._socket.sendto(json.dumps(send_dict), (self._ga_center_host, self._ga_center_port))
        except socket.error, e:
            # errno.EWOULDBLOCK = errno.EAGAIN = 11
            if e.args[0] == errno.EWOULDBLOCK:
                logger.info('errno.EWOULDBLOCK')
            else:
                logger.error('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())

    def _send_ga_data(self, request):
        logger.debug('ga_id:%s', self._ga_id)

        if not self._ga_id:
            return

        if not self._is_ga_request(request):
            return

        try:
            send_dict = self._gen_send_dict(request)
            self.send_data_to_ga_center(send_dict)
        except Exception, e:
            logger.error('exception occur. msg[%s], traceback[%s]', str(e), __import__('traceback').format_exc())

    def _is_ga_request(self, request):
        """
        request是否要被统计
        """

        # 先判断是否在forbid列表里，只要发现就直接拒绝
        for pattern in self._ga_forbid_paths:
            if re.match(pattern, request.path):
                logger.debug('path is in forbid paths. patten: %s, path: %s', pattern, request.path)
                return False

        # 只有allow列表不为空的情况下，才有效
        if self._ga_allow_paths:
            for pattern in self._ga_allow_paths:
                if re.match(pattern, request.path):
                    return True
            else:
                logger.debug('path is not in allow paths. path: %s', request.path)
                return False

        return True

    def _gen_send_dict(self, request):
        """
        生成发送的dict
        """
        ga_referrer_path = ''
        if request.META.get('HTTP_REFERER', ''):
            try:
                parse_result = urlparse.urlparse(request.META['HTTP_REFERER'])
                ga_referrer_path = '/%s%s' % (parse_result.netloc, parse_result.path)
            except Exception, e:
                logger.info('urlparse fail. e: %s', e)

        if getattr(request, 'ga_begin_time', None):
            load_time = int((time.time()-request.ga_begin_time) * 1000)
        else:
            load_time = 0

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

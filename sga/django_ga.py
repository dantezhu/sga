# -*- coding: utf-8 -*-

"""
django插件，绑定之后可以自动给本地的ga_agent发送数据
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
from ga_adapter import GAAdapter


class DjangoGA(GAAdapter):

    def __init__(self):
        super(DjangoGA, self).__init__()

        self._ga_id = getattr(settings, 'GA_ID', None)
        self._ga_agent_host = getattr(settings, 'GA_AGENT_HOST', None) or constants.GA_AGENT_HOST
        self._ga_agent_port = getattr(settings, 'GA_AGENT_PORT', None) or constants.GA_AGENT_PORT
        self._ga_forbid_paths = getattr(settings, 'GA_FORBID_PATHS', None)
        self._ga_allow_paths = getattr(settings, 'GA_ALLOW_PATHS', None)
        self._ga_hack_paths = getattr(settings, 'GA_HACK_PATHS', None)
        self._ga_logger_name = getattr(settings, 'GA_LOGGER_NAME', None)

    def process_request(self, request):
        request.ga_begin_time = time.time()

    def process_response(self, request, response):
        """
        无论是否抛出异常，都会执行这一步
        """
        self._send_ga_data(request)
        return response

    @property
    def logger(self):
        return logging.getLogger(self._ga_logger_name or 'django_ga')

    def _send_ga_data(self, request):
        self.logger.debug('ga_id:%s', self._ga_id)

        if not self._ga_id:
            return False

        if not self.is_ga_request(request.path):
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
                path=self.hack_path(request.path),
                load_time=load_time,
            ),
            visitor=dict(
                __ga=True,
                ip_address=request.META.get('REMOTE_ADDR', ''),
            ),
        )

        return send_dict

# -*- coding: utf-8 -*-

from django.views.generic import View
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

import redis, re

class RedisStatsView(View):
    dbs_rx = re.compile(r'^db(\d+)$', flags=re.U)
    def get_info(self):
        if not hasattr(settings, "CACHES"):
            return {}
        
        caches = {}
        for name, options in getattr(settings, 'CACHES').iteritems():
            if 'BACKEND' not in options or 'RedisCache' not in options['BACKEND']:
                print 1
                continue

            cachedict = {}
            try:
                if "LOCATION" in options and ":" in options['LOCATION']:
                    host, port = options['LOCATION'].split(':')
                    cachedict['port'] = int(port)
                    cachedict['host'] = host
                else:
                    cachedict['port'] = 6379
                    cachedict['host'] = 'localhost'

            except (ValueError, TypeError):
                raise ImproperlyConfigured("port value must be an integer")

            options = options.get('OPTIONS', {})
            try:
                cachedict['db'] = int(options.get('DB', 1))
            except (ValueError, TypeError):
                raise ImproperlyConfigured("db value must be an integer")

            caches[name] = cachedict

        def parse_dbs(infoobject):
            dbs = {}
            for key, value in infoobject.iteritems():
                rx_match = self.dbs_rx.match(key)
                if rx_match:
                    dbs[str(rx_match.group(1))] = value

            return dbs
        
        caches_info = {}
        for name, options in caches.iteritems():
            rclient = redis.Redis(**options)
            caches_info[name] = rclient.info()
            caches_info[name]['dbs'] = parse_dbs(caches_info[name])
            caches_info[name]['options'] = options

        return caches_info

    def get(self, request):
        return render_to_response("redis_cache/stats.html", {},
            context_instance=RequestContext(request))

    
    def post(self, request):
        context = {'info':self.get_info()}
        return render_to_response("redis_cache/stats_include.html", context,
            context_instance=RequestContext(request))

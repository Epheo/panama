#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pprint
import json

class View(object):

    def service_list(self, service_list):
        print('service LIST:')
        for service in service_list:
            print(service)
        print('')

    def service_information(self, action, name, *argv):
        print('%s service %s' % (action, name) )

    def display_stream(self, line):
        jsonstream =  json.loads(line.decode())
        stream = jsonstream.get('stream')
        error = jsonstream.get('error')
        if not error == None:
            print(error)
        if not stream == None:
            print(stream)

    def stopping(self, tag):
        print('Stoping container %s ...' % (tag))

    def removing(self, tag):
        print('Removing container %s ...' % (tag))

    def notlaunched(self, tag):
        print('Services %s not launched' % (tag))

    def ip(self, tag, ipaddr):
        print('Container %s on IP: %s' % (tag, ipaddr))
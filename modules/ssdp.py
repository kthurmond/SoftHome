#   Copyright 2014 Dan Krause
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License..

import socket
from http.client import HTTPResponse
import os


class SSDPResponse(object):

    def __init__(self, sock):
        r = HTTPResponse(sock)
        r.begin()
        self.location = r.getheader("location")
        self.usn = r.getheader("usn")
        self.st = r.getheader("st")
        self.cache = r.getheader("cache-control").split("=")[1]

    def __repr__(self):
        return "<SSDPResponse({location}, {st}, {usn})>".format(**self.__dict__)


def discover(service, timeout=2, retries=1, mx=3):
    group = ("239.255.255.250", 1900)
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: {0}:{1}',
        'MAN: "ssdp:discover"',
        'ST: {st}', 'MX: {mx}', '', ''])
    socket.setdefaulttimeout(max(timeout, mx))
    responses = {}
    for _ in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.sendto(message.format(*group, st=service, mx=mx).encode(), group)
        while True:
            try:
                response = SSDPResponse(sock)
                responses[response.location] = response
            except socket.timeout:
                break
    return list(responses.values())


def parse_ip_address(ip_string):
    start_i = ip_string.find('//')

    if start_i < 0 or start_i > 10:
        if not ip_string[0].isnumeric():
            return -1
        else:
            start_i = 0
    else:
        start_i = start_i + 2

    return_ip = ip_string.lstrip(ip_string[:start_i])

    end_i = return_ip.find(':')
    if end_i < 0:
        end_i = return_ip.find('/')
    if end_i > 0:
        return_ip = return_ip[:end_i]

    return return_ip

def build_discovered(file, service, timeout=2, retries=1, mx=3):
    discoveries = discover(service, timeout, retries, mx)

    ip_addresses = [parse_ip_address(discovery.location) for discovery in discoveries]
    file_obj = open(file, 'w')
    file_obj.writelines(ip_addresses)
    file_obj.close()



# Example:
# import ssdp
# ssdp.discover("roku:ecp")

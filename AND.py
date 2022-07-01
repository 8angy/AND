'''
MIT License

AND (Android Netcat Dumper)

Copyright (c)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

    AND - Android Netcat Dumper
    michael.bangham3@gmail.com

    * Forensically dump the file system, a directory or file from an Android device to a tar.gz archive.
    * Uses the native Android binary toybox for tarring and piping the data out.
    * Pass an optional argument of -b to push busybox to the device for devices that do not have toybox

'''

__version__ = 0.01
__description__ = 'AND (Android NetCat Dumper)'


import socket
import os
import ipaddress
from subprocess import Popen, STDOUT, PIPE, check_output
import sys
from os.path import join as pj
from os.path import abspath, isdir
import time
import argparse


class NetCat:
    def __init__(self, ip, port, out):
        self.output = out
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((ip, int(port)))
        self.socket.settimeout(4)

    def read(self, length=4096):
        # read 4096 bytes at a time to our tar file
        total_dumped = 0
        with open(self.output, 'wb') as f:
            while True:
                try:
                    part = self.socket.recv(length)
                    if not part:
                        break
                    f.write(part)
                    total_dumped += len(part)
                except:
                    break
        self.close()
        return total_dumped

    def write(self, bytes_obj):
        self.socket.sendall(bytes_obj)
        self.close()
        return len(bytes_obj)

    def close(self):
        self.socket.close()


def push_busybox():  # push busybox to the device
    p = Popen('adb push busybox /data/local/tmp', shell=True, stdout=PIPE, stderr=STDOUT)
    p.wait()
    # give busybox permission to execute
    p = Popen('adb shell "su -c chmod 777 /data/local/tmp/busybox"', shell=True, stdout=PIPE, stderr=STDOUT)
    p.wait()
    # check busybox works
    p = Popen('adb shell "su -c /data/local/tmp/busybox"', shell=True, stdout=PIPE, stderr=STDOUT)
    stdout = p.stdout.read().decode()
    if not 'denied' in stdout:
        print('[*] Successfully pushed busybox to /data/local/tmp')
        return True
    return False


def dump(path, busybox, ip, port, out):
    p = Popen('adb forward tcp:{0} tcp:{0}'.format(port), shell=True, stdout=PIPE, stderr=STDOUT)
    p.wait()

    if busybox:
        if push_busybox():
            binary = '/data/local/tmp/busybox'
        else:
            return False
    else:
        binary = 'toybox'

    # create our pipe on the device. It is listening for a connection from the host
    Popen('adb shell "su -c {0} tar -czh {1} | {0} nc -l -p {2}"'.format(binary, path, port))
    # delay to ensure the subprocess has executed initially
    time.sleep(2)
    # execute a shell on the host to accept the pipe, output the data to the host
    nc = NetCat(ip, port, out)
    total_dumped = nc.read()
    return total_dumped


if __name__ == '__main__':
    print("Append the '--help' command to see usage in detail")
    parser = argparse.ArgumentParser(description=__description__)
    parser.add_argument('-i', required=True, help="The absolute path to the Android dir/file. e.g. 'data/data'"
                                                  "For a full file system, enter '.'")
    parser.add_argument('-b', default='toybox', required=False, help="Push busybox to /data/local/tmp. "
                                                                     "Supply 'busybox', default is 'toybox'")
    parser.add_argument('-p', default='5555', required=False, help="Optional port, default is 5555")
    parser.add_argument('-a', default='127.0.0.1', required=False, help="Host IP, default localhost: 127.0.0.1")
    parser.add_argument('-o', default=abspath(os.getcwd()), required=False, help="Optional output directory, "
                                                                                 "default is current directory")
    args = parser.parse_args()

    if len(args.i) and args.i != '/':
        if args.i.startswith('/'):
            path = args.i[1:]
        else:
            path = args.i
    else:
        print('[!!] The supplied path for argument for -i is invalid')
        sys.exit()

    # parse optional arguments
    if len(args.b):
        busybox = args.b
    if args.p:
        if len(args.p):
            # make sure port is in the accepted port range 0 - 65534
            if args.p.isdigit() and args.p in [str(x) for x in list(range(0, 65534))]:
                pass
            else:
                print('[!] The supplied address for -p is invalid, defaulting to {}'.format(args.p))
    if args.a:
        if len(args.a):
            if ipaddress.ip_address(str(args.a)):
                pass
            else:
                print('[!] The supplied address for -a is invalid, defaulting to {}'.format(args.a))
    if args.o:
        if len(args.o):
            if isdir(args.o):
                pass
            else:
                print('[!] The output directory supplied for -o is invalid, defaulting to {}'.format(args.o))

    out_fn = 'AND_{}.tar.gz'.format(int(time.time()))

    print('\nDumping...\n')
    td = dump(path, args.b, args.a, args.p, abspath(pj(args.o, out_fn)))
    if td:
        print('\nFinished! Dumped {} bytes\n'.format(td))
    else:
        print('\n[!!] Something went wrong. It may be that toybox does not '
              'exist on this device or busybox is not compatible.\nAborted\n')

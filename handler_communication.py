'''
Created on Jul 15, 2014

@author: smedema
'''


import socket
import threading
from time import sleep
from json import dumps, loads
import logging
import errno
import my_exceptions

BUFSIZE = 4096
INTERVAL = 0.250

class ClientThread(threading.Thread):

    
    def __init__(self, host, port, ID, num_players):
        super(ClientThread, self).__init__()
        self.socket = socket.create_connection((host,port), None)
        self.lock = threading.Lock()
        self.set_values({u'ID': ID})
        self.set_values({u'num_players': num_players})
        self.get_stack = []

        self._stop = threading.Event()
    
    def run(self):
        while not self._stop.is_set():
            sleep(INTERVAL)
            try:
                messages = self.socket.recv(BUFSIZE).split('\n')
            except socket.error as error_:
                if error_[0] == errno.EWOULDBLOCK:
                    continue
                elif error_[0] == errno.WSAECONNRESET:
                    print('I tried to recv something after connection closed, like the dumb computer I am.')
                    break
                else:
                    raise error_
            for message in messages:
                if message == '':
                    continue  
#                 print message
                message_dict = loads(message)
                self.command(message_dict)
            
    def command(self, command_dict):
        if command_dict[u'request'] == u'get':
            self.get_stack.append(command_dict)
        else:
            logging.debug('{}'.format(command_dict))
            pass
    
    def stop(self):
        try:
            with self.lock:
                self.socket.send('{"category":"handler", "request":"quit"}\n')
        except socket.error as error_:
                if error_[0] == errno.WSAECONNRESET:
                    print('No need to tell the handler to quit if it has already closed the connection.')
                else:
                    raise error_
        finally:
            self._stop.set()
    
    def send_message(self, request, values=None):
        to_send_dict = {}
        to_send_dict[u'category'] = u'handler'
        to_send_dict[u'request'] = request
        if values is not None:
            to_send_dict[u'values'] = values
        to_send_str = dumps(to_send_dict) + '\n'
#         print to_send_str
        with self.lock:
            self.socket.send(to_send_str)
    
    def set_values(self, values_dict):
        self.send_message(u'set', values_dict)
        
    def get_value(self, key):
        self.send_message(u'get', values=[key])
        reply = None
        while reply is None:
            sleep(INTERVAL)
            for index in range(len(self.get_stack)):
                for key_, value in self.get_stack[index][u'values'].iteritems():
                    if key_ == key:
                        if self.get_stack[index][u'statuscode'] == 200:
                            reply = value
                            del self.get_stack[index]
                        # elif self.get_stack[index][u'statuscode'] == SomeOtherCode:
                        #     do something appropriate for that code
                        else:
                            raise my_exceptions.HandlerException(self.get_stack[index])
        return reply
        
    
    def append_values(self, values_dict):
        self.send_message(u'append', values_dict)
    
    def set_is_set_up(self, tf):
        self.set_values({u'is_set_up':tf})
    
    def send_contrib(self, contribution):
        self.append_values({u'contributions':contribution})
        
    def report_contribution(self, contribution):
        self.send_message(u'append', {u'contributions': contribution})
        
    
    
    
    
'''
Created on Jun 13, 2014

@author: smedema
'''

import socket
import threading
from os import _exit
from time import sleep
from json import loads, dumps
from socket import errno


HOST = ''
BUFSIZE = 4096
PORT = 11111


class Session(object):
    
    
    def __init__(self):
        self.lock = threading.Lock()
        self.disconnect = threading.Event()
        self.new_message = threading.Event()
        self.players = []
        self._order = []
        self._reward_game = -1
        self._num_players = 0
        self.socket = socket.socket()
        self.socket.bind((HOST, PORT))
        self.socket.listen(0)
        print('Experiment initialized')
        
    def run(self):
        self.connect_players()
        self.disconnect.wait()
        for player in self.players:
            player.socket.close()
            player.stop()
            player.join()
        self.socket.close()
    
    @property
    def order(self):
        return self._order
    @order.setter
    def order(self, value):
        with self.lock:
            if self._order == []:
                self._order = value
    @property
    def reward_game(self):
        return self._reward_game
    @reward_game.setter
    def reward_game(self, value):
        with self.lock:
            if self._reward_game == -1:
                self._reward_game = value
    @property
    def num_players(self):
        return self._num_players
    @num_players.setter
    def num_players(self, value):
        with self.lock:
            if self._num_players == 0:
                self._num_players = value
            elif self._num_players != value:
                #problem!
                pass
    @property
    def IDs(self):
        temp = []
        for player in self.players:
            temp.append(player.ID)
        return temp
    @property
    def IPs(self):
        temp = []
        for player in self.players:
            temp.append(player.IP)
        return temp
    @property
    def all_set_up(self):
        if len(self.players) < self.num_players:
            return False
        for player in self.players:
            if not player.is_set_up:
                return False
        return True
    @property
    def all_contributions(self):
        answer_dict = {}
        for player in self.players:
            answer_dict[player.IP] = player.contributions
        return answer_dict

    def connect_players(self):
        print('Awaiting connections.')
        self._connect_player()
        while self.num_players == 0:
            self.new_message.wait()
        while len(self.players) < self.num_players:
            self._connect_player()
        print('All players present and accounted for.')
    
    def _connect_player(self):
        conn, addr = self.socket.accept()     
        self.players.append(PlayerThread(conn, addr, session=self))
        print('{} connected.'.format(self.players[-1].IP))
        self.players[-1].start()


class PlayerThread(threading.Thread):
    
    
    def __init__(self, conn, addr, session):
        super(PlayerThread, self).__init__()
        self.socket = conn
        self.socket.setblocking(0)
        self.port = addr[1]
        self.session = session
        
        self.IP = addr[0]
        self.ID = ''
        self.is_set_up = False
        self.contributions = []
        
        self._stop = threading.Event()
     
    def message_command(self, message_dict):
        reply_dict = {u'category': u'handler',
                      u'request': message_dict[u'request'],
                      u'statuscode': 200
                      }
        if message_dict[u'request'] == u'quit':
            print('Quit command recved from client.')
            self.stop()
            return None
        elif message_dict[u'request'] == u'set':
            for key, value in message_dict[u'values'].iteritems():
                if hasattr(self, key):
                    setattr(self, key, value)
                elif hasattr(self.session, key):
                    setattr(self.session, key, value)
                else:
                    reply_dict[u'statuscode'] = 404
                    reply_dict[u'statusmessage'] = 'Value "{}" does not exist.'.format(key)
        elif message_dict[u'request'] == u'append':
            for key, value in message_dict[u'values'].iteritems():
                if hasattr(self, key):
                    attr_ = getattr(self, key)
                    attr_.append(value)
                elif hasattr(self.session, key):
                    attr_ = getattr(self.session, key)
                    attr_.append(value)
                else:
                    reply_dict[u'statuscode'] = 404
                    reply_dict[u'statusmessage'] = 'Value "{}" does not exist.'.format(key)
        elif message_dict[u'request'] == u'get':
            reply_dict[u'values'] = {}
            for key in message_dict[u'values']:
                if hasattr(self, key):
                    reply_dict[u'values'][key] = getattr(self, key)
                elif hasattr(self.session, key):
                    reply_dict[u'values'][key] = getattr(self.session, key)
                else:
                    reply_dict[u'values'][key] = None
                    reply_dict[u'statuscode'] = 404
                    reply_dict[u'statusmessage'] = 'Value does not exist.'
        else:
            reply_dict[u'statuscode'] = 404
            reply_dict[u'statusmessage'] = 'Request does not exist.'.format()
        self.session.new_message.set()
        self.session.new_message.clear()
        return reply_dict
    
    def stop(self):
        self._stop.set()
        
    def run(self):
        while not self._stop.is_set():
            sleep(0.250)
            try:
                messages = self.socket.recv(BUFSIZE).split('\n')
            except socket.error as error_:
                if error_[0] == errno.EWOULDBLOCK:
                    continue
                elif error_[0] == 10054 or 104: #errno.WSAECONNRESET:
                    print('Connection closed. Exiting...')
                    self.stop()
                    break
                else:
                    raise error_
            for message in messages:
                if message == '':
                    continue
#                 print message
                message_dict = loads(message)
                if message_dict[u'category'] == u'handler':
                    reply = self.message_command(message_dict)
                else:
                    # something is very wrong
                    print('Recved a message that was not handler category. '
                          'Message:\n{}'.format(message_dict))
                if reply is not None:
#                     print reply
                    try:
                        self.socket.send('{}\n'.format(dumps(reply)))
                    except socket.error as err_:
                        if err_[0] == 32:
                            print('Connection closed. Exiting...')
                            self.stop()
                        else:
                            raise err_
        self.session.disconnect.set()


class QuitterThread(threading.Thread):

    
    def __init__(self):
        super(QuitterThread, self).__init__()
        self._stop = threading.Event()
         
    def run(self):
        while not self._stop.is_set():
            try:
                _ = raw_input()
            except Exception:
                print('Exiting...')
                _exit(0)
             
    def stop(self):
        self._stop.set()
        
        
quitter_thr = QuitterThread()
quitter_thr.start()

while not quitter_thr._stop.is_set():
    try:
        session = Session()
        session.run()
    except Exception as err_1:
#         print('an error happened: {}'.format(err_1))
        try:
            for player in session.players:
                player.socket.close()
            session.socket.close()
        except Exception as err_2:
            print('another error happened: {}'.format(err_2))


quitter_thr.join()
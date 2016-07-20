'''
Created on Jul 17, 2014

@author: smedema
'''

import threading
import json
import socket
from datetime import datetime
from copy import deepcopy
from time import sleep
from Queue import Queue, LifoQueue

BUFSIZE = 4096

class HeartThread(threading.Thread):
    
    
    def __init__(self, et_socket, socket_lock):
        super(HeartThread, self).__init__()
        self._stop = threading.Event()
        self.socket = et_socket
        self.lock = socket_lock
        
    def stop(self):
        self._stop.set()
        
    def run(self, interval=0.250):
        while not self._stop.is_set():
            with self.lock:
                self.socket.send('{"category":"heartbeat"}')
            sleep(interval)
                

class ListenerThread(threading.Thread):
    
    
    def __init__(self, et_socket, socket_lock, q):
        super(ListenerThread, self).__init__()
        self._stop = threading.Event()
        self.socket = et_socket
        self.lock = socket_lock
        self.q = q
            
        
    def stop(self):
        self._stop.set()
        
    def run(self):
        while not self._stop.is_set():
            recv_str = self.socket.recv(BUFSIZE)
            recv_str = recv_str.split('\n')
            for str_ in recv_str:
                if str_ == '':
                    continue
                else:
                    self.q.put(str_)
                    
                    
class ProcessorThread(threading.Thread):
    
    
    def __init__(
            self,
            raw_data_stream,
            set_current_frame,
            calibration_q,
            tracker_q,
            update_states,
            frame_file=None
            ):
        super(ProcessorThread, self).__init__()
        self.frame_file = frame_file
        self.raw_q = raw_data_stream
        self.set_current_frame = set_current_frame
        self.calibration_q = calibration_q
        self.tracker_q = tracker_q
        self.update_states = update_states
    
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            msg = self.raw_q.get().replace('-1.#IND', '0.0')
            msg = json.loads(msg)
            
            if msg[u'statuscode'] in [800, 801, 802]:
                threading.Thread(target=self.update_states, args=(msg,)).start()
                continue
            
            try:
                self.set_current_frame(msg[u'values'][u'frame'])
            except KeyError:
                pass
            else:
                if self.frame_file is not None:
                    self.frame_file.write('{}\n'.format(msg))
                continue
            
            if msg[u'category'] == u'tracker':
                self.tracker_q.put(msg)
            elif msg[u'category'] == u'calibration':
                self.calibration_q.put(msg)
            elif msg[u'category'] == u'heartbeat':
                pass

    def stop(self):
        self._stop.set()



class EyeTribeServer():

    
    def __init__(self, HOST="localhost", port=6555):

        self.socket = socket.create_connection((HOST,port), None)
        self.lock = threading.Lock()
        self.raw_q = Queue()
        self.current_frame = None
        self.calibration_q = EyeTribeQueue()
        self.tracker_q = EyeTribeQueue()
        self.in_push_mode = False
        self.calibration_state_changed = threading.Condition()
        self.display_index_changed = threading.Condition()
        self.tracker_state_changed = threading.Condition()
        
        # make and start the heartbeat thread
        self.heart_thr = HeartThread(self.socket, self.lock)
        self.heart_thr.start()
        
        # make and start the processor thread
        self.processor_thr = ProcessorThread(
                self.raw_q, self._set_current_frame,
                self.calibration_q, self.tracker_q,
                self._update_states
                )
        self.processor_thr.start()
        
        # make and start the listener thread
        self.listener_thr = ListenerThread(self.socket, self.lock, self.raw_q)
        self.listener_thr.start()
    
    def _update_states(self, msg_dict):
        if msg_dict[u'statuscode'] == 800:
            with self.calibration_state_changed:
                self.calibration_state_changed.notify_all()
        elif msg_dict[u'statuscode'] == 801:
            with self.display_index_changed:
                self.display_index_changed.notify_all()
        elif msg_dict[u'statuscode'] == 802:
            with self.tracker_state_changed:
                self.tracker_state_changed.notify_all()
        else:
            print msg_dict
        
    def _set_current_frame(self, frame):
        self.current_frame = frame
        
    def _send_message(self, category, request=None, values=None):
        
        to_send = {}
        to_send[u'category'] = category
        if request is not None: 
            to_send[u'request'] = request
        if values is not None:
            to_send[u'values'] = values
        to_send = json.dumps(to_send)
        with self.lock:
            self.socket.send(to_send)
            
    def _send_calib_msg(self, request, values=None):
        self._send_message(u'calibration', request, values)
        return self.calibration_q.get_item(request, values)
    
    def _send_tracker_msg(self, request, values=None):
        self._send_message(u'tracker', request, values)
        return self.tracker_q.get_item(request, values)
    
    def get_values(self, *args):
        reply = self._send_tracker_msg(u'get', args)
        return reply[u'values']
    
    def get_value(self, arg):
        reply = self._send_tracker_msg(u'get', [arg])
        return reply[u'values'][arg]
    
    def get_frame(self):
        if not self.in_push_mode:
            self.current_frame = None
            self._send_message(u'tracker', u'get', [u'frame'])
            while self.current_frame is None:
                continue
        return self.current_frame
    
    def get_from_frame(self, *args):
        reply = []
        frame = self.get_frame() # @UnusedVariable
        # are empty lists false?
        if args:
            for arg in args:
                arg_str = 'frame'
                for key in arg:
                    arg_str = arg_str + "[u'{}']".format(key)
                reply.append(eval(arg_str))
            return reply
        else:
            return frame 
    
    def get_avg_xy(self):
        return self.get_from_frame([u'avg', u'x'], [u'avg', u'y'])
    
    def get_resolution(self):
        res_dict = self.get_values(u'screenresw', u'screenresh')
        return (res_dict[u'screenresw'], res_dict[u'screenresh'])
    
    def get_pupil_locations(self):
        coord_list = self.get_from_frame([u'lefteye',u'pcenter',u'x'],
                                         [u'lefteye',u'pcenter',u'y'],
                                         [u'righteye',u'pcenter',u'x'],
                                         [u'righteye',u'pcenter',u'y']
                                         )
        return ((coord_list[0], coord_list[1]), (coord_list[2], coord_list[3]))
    
    def clear_calibration(self):
        return self._send_calib_msg(u'clear')
        
    def start_calibration(self, num_calib_points):
        return self._send_calib_msg(u'start', {u'pointcount':num_calib_points})
            
    def start_calib_point(self, x, y):
        return self._send_calib_msg(u'pointstart', {u'x': x, u'y': y})
            
    def end_calib_point(self):
        return self._send_calib_msg(u'pointend')
    
    def abort_calibration(self):
        return self._send_calib_msg(u'abort')
    
    def set_push(self, bool_):
        self.in_push_mode = bool_
        return self._send_tracker_msg(u'set', {u'push': bool_})
    
    def record_data_to(self, file_):
        '''MUST be an open file object set to 'w' or 'a'
        or None to not record anything'''
        self.processor_thr.frame_file = file_
        
    def est_cpu_minus_tracker_time(
            self,
            num_samples=200,
            cpu_diff_tolerance=0.001,
            sample_interval=0.016
            ):
        yr_mnth_day_hr = datetime.now().isoformat(' ').split(':')[0]
        before_times = []
        tracker_times = []
        after_times = []
        for _ in range(num_samples+1):
            before_times.append(datetime.now().isoformat(' '))
            tracker_times.append(self.get_frame()[u'timestamp']) 
            after_times.append(datetime.now().isoformat(' '))
            sleep(sample_interval)
        avg_cpu_minus_tracker_time = 0
        for i in range(num_samples):
            if tracker_times[i] == tracker_times[i+1]:
                continue
            before_ls = str(before_times[i]).split(':')
            tracker_ls = tracker_times[i].split(':')
            after_ls = str(after_times[i]).split(':')
            if (before_ls[0] != yr_mnth_day_hr or
                tracker_ls[0] != yr_mnth_day_hr or
                after_ls[0] != yr_mnth_day_hr
                ):
                return False
            before = float(before_ls[-2])*60 + float(before_ls[-1])
            tracker = float(tracker_ls[-2])*60 + float(tracker_ls[-1])
            after = float(after_ls[-2])*60 + float(after_ls[-1])
            if after-before > cpu_diff_tolerance:
                continue
            avg_cpu_minus_tracker_time += ((before+after)/2 - tracker)
        avg_cpu_minus_tracker_time /= num_samples
        return avg_cpu_minus_tracker_time


class CalibrationError(Exception):
    
    
    def __init__(self, err_msg):
        self.err_msg = err_msg
        
    def __str__(self):
        return self.err_msg
    
    
class EyeTribeQueue(LifoQueue):
    
    
    def get(self, block=True, timeout=None):
        # fail horribly
        raise Exception('You cannot use the normal "get" function in '
                        'an EyeTribeQueue.')
            
    def get_item(self, request, values=None):
        self.not_empty.acquire()
        try:
            while True: 
                for i in range(self._qsize()):
                    if self.queue[i][u'request'] == request:
                        if request == u'get' and set(self.queue[i][u'values']) != set(values):
                            continue
                        item = deepcopy(self.queue[i])
                        del self.queue[i]
                        self.not_full.notify()
                        return item
                self.not_empty.wait()
        finally:
            self.not_empty.release()

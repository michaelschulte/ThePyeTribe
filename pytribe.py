'''
Created on Jul 28, 2014

@author: smedema
'''

import threading
import json
import socket
from datetime import datetime
from copy import deepcopy
from time import sleep
from Queue import Queue, LifoQueue


class HeartThread(threading.Thread):
    
    '''Sends "heartbeats," i.e. keepalives, to the eye tribe server.'''
    
    def __init__(self, beat_function, interval=0.250):
        '''Initialize the class.
        
        Keyword arguments:
        beat_function -- this thread is supposed to be incapable of working
            on its own without a proper EyeTribeServer object. We don't
            want to directly give it access to the socket or threading lock
            for compartmentalization reasons.
        interval -- the interval in between sending heartbeats
            (default 0.250 seconds)
        '''
        super(HeartThread, self).__init__()
        self.beat = beat_function
        self.interval = interval
        self._stop = threading.Event()
        
    def stop(self):
        '''Set the stop flag.'''
        self._stop.set()
        
    def run(self):
        '''Keep on beating every {interval}.'''
        while not self._stop.is_set():
            self.beat()
            sleep(self.interval)
                

class ListenerThread(threading.Thread):
    
    '''Continually listens for messages from the eye tribe server,
    and puts these into a Queue to be processed.
    '''
    
    def __init__(self, recv_function, q):
        '''Initialize the function.
        
        Keyword arguments:
        recv_function -- this thread is supposed to be incapable of working
            on its own without a proper EyeTribeServer object. We don't
            want to directly give it access to the socket or threading lock
            for compartmentalization reasons.
        q -- a Queue to put stuff in.
        '''
        super(ListenerThread, self).__init__()
        self.recv_function = recv_function
        self.q = q
        self._stop = threading.Event()
            
        
    def stop(self):
        '''Set the stop flag.'''
        self._stop.set()
        
    def run(self):
        '''Put anything from the socket into the Queue, separating on
        newlines.
        '''
        while not self._stop.is_set():
            recv_str = self.recv_function()
            recv_strs = recv_str.split('\n')
            for str_ in recv_strs:
                if str_ == '':
                    continue
                else:
                    self.q.put(str_)
                    
                    
class ProcessorThread(threading.Thread):
    
    '''Takes the stuff from the Listener Thread's Queue and figures
    out what to do with it.
    '''
    
    def __init__(self,
                 raw_data_stream,
                 set_current_frame,
                 calibration_q,
                 tracker_q,
                 update_states,
                 frame_file=None):
        super(ProcessorThread, self).__init__()
        
        self._frame_file = frame_file
        self.raw_q = raw_data_stream
        self.set_current_frame = set_current_frame
        self.calibration_q = calibration_q
        self.tracker_q = tracker_q
        self.update_states = update_states
        
        self._frame_file_lock = threading.Lock()
        self._stop = threading.Event()
        
    @property
    def frame_file(self):
        return self._frame_file
    @frame_file.setter
    def frame_file(self, file_):
        if file_ is not self._frame_file:
            with self._frame_file_lock:
                if self._frame_file is not None:
                    self._frame_file.flush()
                self._frame_file = file_
            
        

    def run(self):
        while not self._stop.is_set():
            raw_msg = self.raw_q.get().replace('-1.#IND', '0.0')
            msg = json.loads(raw_msg)
            
            if msg[u'statuscode'] in [800, 801, 802]:
                threading.Thread(target=self.update_states, args=(msg,)).start()
                continue
            
            if u'values' in msg.keys() and u'frame' in msg[u'values'].keys():
                self.set_current_frame(msg[u'values'][u'frame'])
                if self._frame_file is not None:
                    with self._frame_file_lock:
                        self._frame_file.write('{}\n'.format(msg))
                continue
        
            if msg[u'category'] == u'tracker':
                self.tracker_q.put(msg)
            elif msg[u'category'] == u'calibration':
                self.calibration_q.put(msg)
            elif msg[u'category'] == u'heartbeat':
                # could be used for error checking
                pass
            else:
                # error?
                pass

    def stop(self):
        self._stop.set()



class EyeTribeServer(object):

    '''Contains all the methods and properties necessary to make use
    of the eye tribe tracker with Python.
    '''
    
    def __init__(self, HOST="localhost", port=6555, BUFSIZE=4096):

        self.socket = socket.create_connection((HOST,port), None)
        self.lock = threading.Lock()
        self.raw_q = Queue()
        self._current_frame = None
        self.calibration_q = EyeTribeQueue()
        self.tracker_q = EyeTribeQueue()
        self._in_push_mode = False
        self.calibration_state_changed = threading.Condition()
        self.display_index_changed = threading.Condition()
        self.tracker_state_changed = threading.Condition()
        
        # make and start the heartbeat thread
        self.heart_thr = HeartThread(
                beat_function=lambda: self._send_message(u'heartbeat')
                )
        self.heart_thr.start()
        
        # make and start the processor thread
        self.processor_thr = ProcessorThread(
                self.raw_q, self._set_current_frame,
                self.calibration_q, self.tracker_q,
                self._update_states
                )
        self.processor_thr.start()
        
        # make and start the listener thread
        self.listener_thr = ListenerThread(
                recv_function=lambda: self.socket.recv(BUFSIZE),
                q=self.raw_q
                )
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
        self._current_frame = frame
        
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
    
    def _get_value(self, value_):
        reply = self._send_tracker_msg(u'get', [value_])
        return reply[u'values'][value_]
    
    def _set_value(self, key_, value_):
        return self._send_tracker_msg(u'set', {key_: value_})
    
    def _get_values(self, *args):
        reply = self._send_tracker_msg(u'get', args)
        to_return = [None]*len(args)
        for index, arg in enumerate(args):
            to_return[index] = reply[u'values'][arg]
        return to_return
    
    def _set_values(self, **kwargs):
        return self._send_tracker_msg(u'set', kwargs)
    
    @property
    def push(self):
        return self._in_push_mode
    @push.setter
    def push(self, bool_):
        self._in_push_mode = bool_
        return self._set_value(u'push', bool_)
    
    @property
    def heartbeatinterval(self):
        return self._get_value(u'heartbeatinterval')
    @heartbeatinterval.setter
    def heartbeatinterval(self, value_):
        raise ImmutableException('heartbeatinterval')
    
    @property
    def version(self):
        return self._get_value(u'version')
    @version.setter
    def version(self, int_):
        return self._set_value(u'version', int_)
    
    @property
    def trackerstate(self):
        return self._get_value(u'trackerstate')
    @trackerstate.setter
    def trackerstate(self, value_):
        raise ImmutableException('trackerstate')
    
    @property
    def framerate(self):
        return self._get_value(u'framerate')
    @framerate.setter
    def framerate(self, value_):
        raise ImmutableException('framerate')
    
    @property
    def iscalibrated(self):
        return self._get_value(u'iscalibrated')
    @iscalibrated.setter
    def iscalibrated(self, value_):
        raise ImmutableException('iscalibrated')
    
    @property
    def iscalibrating(self):
        return self._get_value(u'iscalibrating')
    @iscalibrating.setter
    def iscalibrating(self, value_):
        raise ImmutableException('iscalibrating')
    
    @property
    def calibresult(self):
        return self._get_value(u'calibresult')
    @calibresult.setter
    def calibresult(self, value_):
        raise ImmutableException('calibresult')
    
    @property
    def frame(self):
        if not self._in_push_mode:
            self._current_frame = None
            self._send_message(u'tracker', u'get', [u'frame'])
            while self._current_frame is None:
                continue
        return self._current_frame
    @frame.setter
    def frame(self, value_):
        raise ImmutableException('frame')
    
    @property
    def screenindex(self):
        return self._get_value(u'screenindex')
    @screenindex.setter
    def screenindex(self, int_):
        return self._set_value(u'screenindex', int_)
    
    @property
    def screenresw(self):
        return self._get_value(u'screenresw')
    @screenresw.setter
    def screenresw(self, int_):
        return self._set_value(u'screenresw', int_)
    
    @property
    def screenresh(self):
        return self._get_value(u'screenresh')
    @screenresh.setter
    def screenresh(self, int_):
        return self._set_value(u'screenresh', int_)
    
    @property
    def screenpsyw(self):
        return self._get_value(u'screenpsyw')
    @screenpsyw.setter
    def screenpsyw(self, float_):
        return self._set_value(u'screenpsyw', float_)
    
    @property
    def screenpsyh(self):
        return self._get_value(u'screenpsyh')
    @screenpsyh.setter
    def screenpsyh(self, float_):
        return self._set_value(u'screenpsyh', float_)
    
    @property
    def screenres(self):
        return self._get_values(u'screenresw', u'screenresh')
    @screenres.setter
    def screenres(self, arg1, arg2=None):
        if type(arg1) == list or type(arg1) == tuple:
            if len(arg1) == 2:
                return self._set_values(
                        screenresw=arg1[0], screenresh=arg1[1]
                        )
        elif arg2 is not None:
            return self._set_values(screenresw=arg1, screenresh=arg2)
    
    def get_avg_xy(self):
        frame_ = self.frame
        return (frame_[u'avg'][u'x'], frame_[u'avg'][u'y'])
    
    def get_pupil_locations(self):
        frame_ = self.frame
        lefteye = (frame_[u'lefteye'][u'pcenter'][u'x'],
                   frame_[u'lefteye'][u'pcenter'][u'y'])
        riteeye = (frame_[u'righteye'][u'pcenter'][u'x'],
                   frame_[u'righteye'][u'pcenter'][u'y'])
        return (lefteye, riteeye)
    
    def clear_calibration(self):
        return self._send_calib_msg(u'clear')
        
    def start_calibration(self, num_calib_points):
        return self._send_calib_msg(u'start', {u'pointcount': num_calib_points})
            
    def start_calib_point(self, x, y):
        return self._send_calib_msg(u'pointstart', {u'x': x, u'y': y})
            
    def end_calib_point(self):
        return self._send_calib_msg(u'pointend')
    
    def abort_calibration(self):
        return self._send_calib_msg(u'abort')
    
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
        if self.push:
            # Fail by raising an exception
            # DON'T just return False. That means something else.
            # (see below)
            pass
        yr_mnth_day_hr = datetime.now().isoformat(' ').split(':')[0]
        before_times = []
        tracker_times = []
        after_times = []
        for _ in range(num_samples+1):
            before_times.append(datetime.now().isoformat(' '))
            tracker_times.append(self.frame[u'timestamp']) 
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
                # If this ever happens, it means the hour just advanced
                # by one. Instead of trying to account for that, it
                # makes more sense to just assume it will almost never
                # happen, and if it does, it can't possibly happen
                # again for another hour, so we return False and the
                # function that calls THIS function just tries again.
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
    
    
class ImmutableException(Exception):
    
    
    def __init__(self, tried_to_set):
        self.err_msg = 'You cannot set '\
        '{}, it is defined by TheEyeTribe server.'.format(tried_to_set)
        
    def __str__(self):
        return self.err_msg
    
    
class EyeTribeQueue(LifoQueue):
    
    '''A special Queue that only allows get_item() and not get(),
    so that you can get an item with a specific attribute from the
    Queue.
    
    Inherits from LifoQueue because that uses a basic list as its
    underlying data structure, enabling easy search. The reason we
    inherit from a Queue at all is because this needs to be
    thread-safe, and Queues already have most of that machinery in
    place.
    '''    
    
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

'''
Created on May 28, 2014

@author: smedema
'''

from copy import deepcopy
import datetime



class Packet():
    '''
    classdocs
    '''
    CONTRIB_MODE = 0
    FEEDBACK_MODE = 1
    
    which_mode = CONTRIB_MODE
    which_round = 1
    


    def __init__(self, values=""):
        self.time = datetime.datetime.now().isoformat(' ')
        self.values = values
        self.round = deepcopy(Packet.which_round)
        self.mode = deepcopy(Packet.which_mode)
        
    def getXY(self):
        return (self.values[u'frame'][u'avg'][u'x'],
                self.values[u'frame'][u'avg'][u'y'])
    
    
    
    
    
    
    
    
    
'''
Created on Jul 7, 2014

@author: smedema
'''

class EscPressedException(Exception):


    def __init__(self):
        pass
        
    def __str__(self):
        return 'Escape key pressed.'
    
class HandlerException(Exception):
    
    
    def __init__(self, err):
        self.err = err
    
    def __str__(self):
        return 'Handler error: {}'.format(self.err)
    

class EyeTribeException(Exception):
    
    
    def __init__(self):
        pass
    
    def __str__(self):
        return 'EyeTribe error.'
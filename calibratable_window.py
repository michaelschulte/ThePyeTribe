'''
Created on Jul 1, 2014

@author: smedema
'''

from random import shuffle

from psychopy.visual import Window, Circle
from psychopy.core import wait, getTime


class CalibratableWindow(Window):


    def __init__(self,
                 num_calib_points=9,
                 margin=100,
                 **kwargs
                 ):
        super(CalibratableWindow, self).__init__(                                
                **kwargs
                )
        self.hres = int(self.size[0])
        self.vres = int(self.size[1])
        self.num_calib_points = num_calib_points
        self.margin = margin
        self.calib_points_coords = self.gen_calib_point_coords()
        
    def calibrate(self, et_comm):
        self.setMouseVisible(False)
        self.make_points()
        start_reply = et_comm.start_calibration(self.num_calib_points)
        if start_reply[u'statuscode'] == 403:
            et_comm.abort_calibration()
            et_comm.start_calibration(self.num_calib_points)
        calibration_obj={}
        for x,y in self.calib_points_coords:
            self.point_place(x,y)
            wait(0.750)            
            et_comm.start_calib_point(x,y)
            self.point_expand_contract(duration=1)
            calibration_obj = et_comm.end_calib_point()
            wait(0.250)
        self.setMouseVisible(True)
        return calibration_obj[u'values'][u'calibresult']

    def make_points(self):    
        self.outer_point = Circle(self, radius=25)
        self.outer_point.fillColor = 'white'
        self.outer_point.setPos((5000,5000))
        self.inner_point = Circle(self, radius=5)
        self.inner_point.fillColor = 'red'
        self.inner_point.setPos((5000,5000))
    
    def point_place(self, x, y):
        xy_tuple = self.tl2c((x,y))
        self.outer_point.setPos(xy_tuple)
        self.inner_point.setPos(xy_tuple)
        self.outer_point.draw()
        self.inner_point.draw()
        self.flip()
        
    def tl2c(self, coords_tuple):
        x = coords_tuple[0] - self.hres/2
        y = coords_tuple[1] - self.vres/2
        return (x, -y)
            
    def point_expand_contract(self, duration):
        start_time = getTime()
        ratio = 0
        while ratio < 1:
            ratio = (getTime()-start_time)/(duration*0.5)
            self.outer_point.setRadius(25+25*ratio)
            self.outer_point.draw()
            self.inner_point.draw()
            self.flip()
        while ratio < 2:
            ratio = (getTime()-start_time)/(duration*0.5)
            self.outer_point.setRadius(75-25*ratio)
            self.outer_point.draw()
            self.inner_point.draw()
            self.flip()
       
    def gen_calib_point_coords(self):
        if self.num_calib_points == 9:
            nrows = 3
            ncols = 3
        elif self.num_calib_points == 12:
            nrows = 3
            ncols = 4
        elif self.num_calib_points == 16:
            nrows = 4
            ncols = 4
        else:
            print('Unacceptable number of calibration points. '
                  'Please choose 9, 12, or 16. Defaulting to 9.')
            nrows = 3
            ncols = 3
            
        coord_list = []
        h_spacing = (self.hres - 2*self.margin)/(ncols-1)
        v_spacing = (self.vres - 2*self.margin)/(nrows-1)
        for row in range(nrows):
            for col in range(ncols):
                coord_list.append((col*h_spacing + self.margin, row*v_spacing + self.margin))
        shuffle(coord_list)
        return coord_list
    
    
    
    
    
    
    
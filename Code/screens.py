'''
Created on Jun 25, 2014

@author: smedema
'''

import abc
import logging
from math import floor, cos, sin, pi
from random import choice
from random import shuffle # @UnusedImport
from threading import Event

from psychopy.visual import TextStim, ImageStim, Circle, Rect
from psychopy.event import Mouse, xydist, getKeys
from psychopy.core import getAbsTime, wait

import button


class Screen(object):
    __metaclass__  = abc.ABCMeta
    default_font_size = 40
    
    def __init__(self,
                 disp,
                 width=None,
                 height=None,
                 margin=None,
                 font_size=None,
                 wait_time=0
                 ):
        self.window = disp
        self.origin = (0,0)
        self.wait_time = wait_time
        if width is not None:
            self.width = width
        else:
            self.width = self.window.hres
        if height is not None:
            self.height = height
        else:
            self.height = self.window.vres
        if margin is not None:
            self.margin = margin
        else:
            self.margin = self.window.margin
        self.continue_button = button.Button(
                window=self.window,
                pos=self.coords(((self.width - 2*self.margin),
                                 (self.height - 2*self.margin)
                                 ))
                )
        self.move_on_flag = Event()
        self.mouse = Mouse()
        
    def run(self, debug_mode=False):
        self.t0 = getAbsTime()
        while not self.move_on_flag.is_set():
            if self.continue_button.clickable:
                if self.mouse.isPressedIn(self.continue_button._frame, [0]):
                    self.move_on_flag.set()
            elif self.wait_time > 0:
                if getAbsTime() - self.t0 > self.wait_time:
                    self.continue_button.clickable = True
            
            self.draw(debug_mode)
            self.window.flip()
            wait(0.016666, 0.016666)
        self.cleanup()

    @abc.abstractmethod
    def draw(self, debug_mode=False):
        '''To override!'''
        
    def cleanup(self):
        '''To override!'''
        pass
    
    def _cfg_2_pix(self, dimension, cfg_val):
        if cfg_val < 0:
            return dimension + cfg_val
        elif cfg_val <= 1:
            return self.margin + cfg_val*(dimension - 2*self.margin)
        else:
            return cfg_val
    
    def x_cfg_2_pix(self, cfg_val):
        return self._cfg_2_pix(self.width, cfg_val)
    
    def y_cfg_2_pix(self, cfg_val):
        return self._cfg_2_pix(self.height, cfg_val)
    
    def w_cfg_2_pix(self, cfg_val):
        if cfg_val <= 1:
            return cfg_val*(self.width - 2*self.margin)
        else:
            return cfg_val
        
    def h_cfg_2_pix(self, cfg_val):
        if cfg_val <= 1:
            return cfg_val*(self.height - 2*self.margin)
        else:
            return cfg_val
        
    def dict2text_stim(self, cfg):
        try:
            width = self.w_cfg_2_pix(cfg[u'width'])
        except:
            width = None
        text_stim_to_return = TextStim(self.window,
                                       text = cfg[u'text'],
                                       pos = self.coords((self.x_cfg_2_pix(cfg[u'x']),
                                                          self.y_cfg_2_pix(cfg[u'y']))),
                                       height = cfg[u'font_size'],
                                       wrapWidth = width)
        return text_stim_to_return
    
    def coords(self, arg1, arg2=None):
        if arg2 is None:
            coords_tuple = arg1
        else:
            coords_tuple = (arg1, arg2)
        coords_tuple = (coords_tuple[0]+self.origin[0],
                        coords_tuple[1]+self.origin[1])
        return self.window.tl2c(coords_tuple)
    

class BlankScreen(Screen):
    
    
    def __init__(self, disp, duration):
        super(BlankScreen, self).__init__(disp)
        self.duration = duration
        
    def draw(self, debug_mode=False):
        if getAbsTime() - self.t0 > self.duration:
            self.move_on_flag.set()

class FeedbackScreen(Screen):
    
    # This should not be messed with, we want to maintain between-
    # subject counterbalancing, but not change things within-subject.
    reversed = choice([True, False])
    
    def __init__(self,
                 disp,
                 num_players,
                 config_dict,
                 gaze_pos_getter=None,
                 width=None,
                 height=None,
                 margin=None,
                 font_size=None,
                 col_x_list=[],
                 AOIs=False):
        super(FeedbackScreen, self).__init__(disp)
        self.gaze_pos_getter = gaze_pos_getter
        self.continue_button.clickable = True
        
        cfg = config_dict[u'feedback_screen']
        if width is not None:
            self.width = width
        else:
            self.width = self.window.hres
        if height is not None:
            self.height = height
        else:
            self.height = self.window.vres
        if margin is not None:
            self.margin = margin
        else:
            self.margin = self.window.margin
        if font_size is not None:
            self.font_size = font_size
        else:
            self.font_size = config_dict[u'feedback_screen'][u'font_size']
        self.col_x_list = []
        if col_x_list == []:
            self.col_x_list.append(
                    self.x_cfg_2_pix(
                            config_dict[u'feedback_screen'][u'left_col_x']
                    ))
            self.col_x_list.append(
                    self.x_cfg_2_pix(
                            config_dict[u'feedback_screen'][u'midd_col_x']
                    ))
            self.col_x_list.append(
                    self.x_cfg_2_pix(
                            config_dict[u'feedback_screen'][u'rite_col_x']
                    ))
            del col_x_list
        if FeedbackScreen.reversed:
            self.col_x_list.reverse()
        
        self.gaze = Circle(self.window, radius=5)
        self.gaze.fillColor = 'red'
        
        self.nrows = num_players + 3
        self.SUMROWINDEX = self.nrows - 2
        self.AVGROWINDEX = self.nrows - 1
        
        row_spacing = (self.height - 2*self.margin)/(self.nrows-1)
        
        
        
        self.contr_col = []
        self.label_col = []
        self.payof_col = []
        
        for i in range(self.nrows):
            y = self.window.margin + i*row_spacing
            temp_contr = TextStim(self.window, height=self.font_size)
            temp_label = TextStim(self.window, height=self.font_size)
            temp_payof = TextStim(self.window, height=self.font_size)
            if i == 0:
                temp_contr.setText(cfg[u'contributions'])
                temp_label.setText(cfg[u'players'])
                temp_payof.setText(cfg[u'payoffs'])
            else:
                temp_contr.setText('xx')
                temp_payof.setText('xx')
                if i == 1:
                    temp_label.setText(cfg[u'you'])
                elif i <= num_players:
                    temp_label.setText(cfg[u'others'][i-2])
                elif i == self.SUMROWINDEX:
                    temp_label.setText(cfg[u'sum'])
                elif i == self.AVGROWINDEX:
                    temp_label.setText(cfg[u'average'])
                else:
                    logging.error('Error in FeedbackScreen.__init__(). Wrong number of rows?')
            temp_contr.setPos(self.coords((self.col_x_list[0], y)))
            self.contr_col.append(temp_contr)
            temp_label.setPos(self.coords((self.col_x_list[1], y)))
            self.label_col.append(temp_label)
            temp_payof.setPos(self.coords((self.col_x_list[2], y)))
            self.payof_col.append(temp_payof)
            
            self.AOIs = []
            if AOIs:
                for _ in range(3):
                    self.AOIs.append(Rect(self.window,
                                          width=400,
                                          height=280,
                                          lineColor='slateblue',
                                          fillColor='steelblue'))
                self.AOIs[-1].setPos(self.contr_col[-1].pos)
                self.AOIs[-2].setPos(self.label_col[-1].pos)
                self.AOIs[-3].setPos(self.payof_col[-1].pos)
        
                
    def draw(self, debug_mode=False):
        if getAbsTime() - self.t0 > 30:
            self.move_on_flag.set()
            
        if self.AOIs != [] and self.gaze_pos_getter is not None:
            self.gaze.pos = self.coords(self.gaze_pos_getter())
            for shape in self.AOIs:
                if shape.contains(self.gaze.pos):
                    shape.setFillColor('slateblue')
                else:
                    shape.setFillColor('steelblue')
            for shape in self.AOIs:
                shape.draw()
            self.gaze.draw()
            
        
        for i in range(self.nrows):
            self.label_col[i].draw()
            self.contr_col[i].draw()
            self.payof_col[i].draw()
        self.continue_button.draw()
            
    def cleanup(self):
        self.move_on_flag.clear()
            
    def update_info(self, contr_avg, payoff_avg, contr_sum, payoff_sum, my_contr, my_payoff, other_contr=[], other_payoff=[]):
        # This bit randomizes the order that the other players are
        # presented in on the feedback screen. Not yet tested to
        # make sure it works, but it should. Only matters if N > 2.
#         if len(other_contr) > 1:
#             indices = []
#             for i in range(len(other_contr)):
#                 indices.append(i)
#             shuffle(indices)
#             temp_contr = other_contr[:]
#             temp_payoff = other_payoff[:]
#             for i in range(len(indices)):
#                 other_contr[i] = temp_contr[indices[i]]
#                 other_payoff[i] = temp_payoff[indices[i]]

        self.update_col(self.contr_col, contr_avg, contr_sum, my_contr, other_contr)
        self.update_col(self.payof_col, payoff_avg, payoff_sum, my_payoff, other_payoff)
    
    def update_col(self, col, avg, sum_, mine, others):
#         avg = str(avg).replace('.',',')
        avg = '{:n}'.format(avg)
        sum_ = '{:n}'.format(sum_)
        mine = '{:n}'.format(mine)
        col[self.AVGROWINDEX].setText(avg)
        col[self.SUMROWINDEX].setText(sum_)
        col[1].setText(mine)
        for i in range(len(others)):
            other = '{:n}'.format(others[i])
            col[i+2].setText(other)

            
class ContribScreen(Screen):
    
    def __init__(self,
                 disp,
                 text,
                 config_dict,
                 gaze_pos_getter=None,
                 width=None,
                 height=None,
                 margin=None,
                 font_size=None,
                 choice_font_size=100,
                 origin=None
                 ):
        super(ContribScreen, self).__init__(disp)
        cfg = config_dict[u'contrib_screen']
        self.gaze_pos_getter = gaze_pos_getter
        self.instr_text_preformat = text
        self.contrib_choice = '__'
        if width is not None:
            self.width = width
        else:
            self.width = self.window.hres
        if height is not None:
            self.height = height
        else:
            self.height = self.window.vres
        if margin is not None:
            self.margin = margin
        else:
            self.margin = self.window.margin
        if origin is not None:
            self.origin = origin
        if font_size is None:
            font_size = config_dict[u'contrib_screen'][u'text'][u'font_size']
        
        self.contrib_choices = self.gen_contrib_choices(
                cfg[u'nrows'], cfg[u'ncols'], font_size=choice_font_size
                )
        self.contrib_instructions = TextStim(
                self.window, height=font_size,
                text=self.instr_text_preformat.format(self.contrib_choice),
                pos=self.coords((self.x_cfg_2_pix(cfg[u'text'][u'x']),
                               self.y_cfg_2_pix(cfg[u'text'][u'y'])
                               )),
                wrapWidth=self.w_cfg_2_pix(cfg[u'text'][u'width'])
                )
        
        self.gaze = Circle(self.window, radius=5)
        self.gaze.fillColor = 'red'
    
        
    def draw(self, debug_mode=False): 
        mouseX, mouseY = self.mouse.getPos()
        for text_stim in self.contrib_choices:
            if xydist((mouseX, mouseY), text_stim.pos) < self.mouseover_threshold:
                text_stim.color = 'darkorange'
                if self.mouse.getPressed()[0]:
                    self.contrib_choice = text_stim.text
                    self.contrib_instructions.setText(self.instr_text_preformat.format(self.contrib_choice))
                    self.continue_button.clickable = True
            else:
                text_stim.color = 'white'
            text_stim.draw()
        self.continue_button.draw()
        self.contrib_instructions.draw()
        if self.gaze_pos_getter is not None:
            self.gaze.pos = self.coords(self.gaze_pos_getter())
            self.gaze.draw()
        
    def cleanup(self):
        self.continue_button.clickable = False
        self.contrib_instructions.setText(self.instr_text_preformat.format('__'))
        self.move_on_flag.clear()
        
    def gen_contrib_choices(self, nrows, ncols, font_size):
        h_spacing = (self.width - 2*self.margin)/(ncols-1)
        v_spacing = h_spacing
        '''OR: v_spacing = (self.height - 2*self.margin)/(nrows-1)'''
        self.mouseover_threshold = min(h_spacing, v_spacing)/4
        contrib_choices = []
        for i in range(0,nrows*ncols):
            xpos = self.margin + (i%ncols)*h_spacing
            
            '''
            To move the array to the bottom of the page:
            ypos = self.height - self.margin - (nrows-floor(1.0*i/ncols)-1)*v_spacing
            '''
            ypos = floor(1.0*i/ncols)*v_spacing + self.margin
            '''
            1.0*i/ncols gives us a floating-point number. Without the 1.0, python 
            interprets this as int-division and truncates. I could have exploited 
            this for slightly simpler code but it is really stupid that it works 
            that way and who knows what bugs could pop up by relying on something 
            that is in my opinion a bug?
            We take the floor of that number to give us a "row index." We multiply
            this number by the vertical spacing.
            '''
            
            if i < 10:
                temp = ' {} '.format(i)
            else:
                temp = '{}'.format(i)
            contrib_choices.append(TextStim(win=self.window,
                                                 text=temp,
                                                 pos=self.coords((xpos,ypos)),
                                                 height=font_size))
        return contrib_choices
        

class DetectPupilsScreen(Screen):
    
    def __init__(self, disp, text, config_dict, pupil_coords_getter, seconds_to_ok):
        super(DetectPupilsScreen, self).__init__(disp)
        self.continue_button.setPos((0.0,0.0))
        self.pupil_coords_getter = pupil_coords_getter
        cfg = config_dict[u'detect_pupils_screen']
        self.in_range_ctr = 0
        fps = self.window.getActualFrameRate()
        self.ctr_max = fps*seconds_to_ok
        
        self.detect_pupils_instructions = TextStim(
                self.window,
                text=text,
                pos=self.coords((self.x_cfg_2_pix(cfg[u'text'][u'x']),
                               self.y_cfg_2_pix(cfg[u'text'][u'y'])
                               )),
                wrapWidth=self.x_cfg_2_pix(cfg[u'text'][u'width']),
                height=cfg[u'text'][u'font_size']
                )
                                
        self.lefteye = []
        self.lefteye.append(Circle(self.window, radius=50))
        self.lefteye[-1].fillColor='white'
        self.lefteye.append(Circle(self.window, radius=25))
        self.lefteye[-1].fillColor='black'
        
        self.riteeye = []
        self.riteeye.append(Circle(self.window, radius=50))
        self.riteeye[-1].fillColor='white'
        self.riteeye.append(Circle(self.window, radius=25))
        self.riteeye[-1].fillColor='black'
        
#         self.ok_indicator = RadialStim(
#                 self.window, tex='none', mask='gauss', pos=(0,0),
#                 size=(1000,1000), color=[0,0,0.5], opacity=0.5
#                 )

        self.ok_indicator = Circle(
                self.window, radius=(350,200), fillColor='palegreen', 
                opacity=0.05, lineColor=None
                )
        
        self.grid = []
        for x, y in self.window.calib_points_coords:
            self.grid.append(Circle(self.window,
                                    radius=5,
                                    pos=self.coords((x, y)),
                                    lineColor=None,
                                    fillColor='green'
                                    ))

        
    def draw(self, debug_mode=False):
        
        ((leftx,lefty),(ritex,ritey)) = self.pupil_coords_getter()
        
        leftx *= self.window.hres
        lefty *= self.window.vres
        ritex *= self.window.hres
        ritey *= self.window.vres
        
        if leftx == 0.0 or lefty == 0.0:
            leftx, lefty = (-5000,-5000)
        if ritex == 0.0 or ritey == 0.0:
            ritex, ritey = (-5000,-5000)
        for circle in self.lefteye:
            circle.pos = self.coords((leftx,lefty))
        for circle in self.riteeye:
            circle.pos = self.coords((ritex,ritey))
        
#         ldist = xydist([leftx,lefty], (self.window.hres/2,self.window.vres/2))
#         rdist = xydist([ritex,ritey], (self.window.hres/2,self.window.vres/2))
#         if ldist+rdist < self.window.vres/2:
#             self.in_range_ctr += 1

        if (self.ok_indicator.contains(self.lefteye[0].pos) and
            self.ok_indicator.contains(self.riteeye[0].pos)
            ):
            self.in_range_ctr += 1
            op = self.ok_indicator.opacity + 0.03
            self.ok_indicator.opacity = min(op, 0.65)
        else:
            op = self.ok_indicator.opacity - 0.03
            self.ok_indicator.opacity = max(op, 0.05)
#         
#         
#         if missed_flag:
#             temp = self.ok_indicator.color * 0.95
#             temp[2] = 0.5
#             temp[0] = 0
#         else:
#             ratio = self.window.vres/(3*(ldist+rdist))
#             if ratio > 1:
#                 ratio = 1
#             temp = [0, ratio, 0.5]
#  
#         self.ok_indicator.color = temp

        if ((self.in_range_ctr >= self.ctr_max) or 
            debug_mode
            ):
            self.continue_button.clickable = True

        # draw commands
        for thing in self.grid:
            thing.draw()
        self.ok_indicator.draw()
        self.detect_pupils_instructions.draw()
        self.continue_button.draw()

        for circle in self.lefteye:
            circle.draw()
        for circle in self.riteeye:
            circle.draw()
            
            
class InstructionsScreen(Screen):
    
    def __init__(self, disp, text, font_size=40, wait_time=0):
        super(InstructionsScreen, self).__init__(disp, wait_time=wait_time)
        self.instructions_text = TextStim(
                disp, pos=(0,0), text=text, height=font_size,
                wrapWidth=self.w_cfg_2_pix(0.666)
                )
                                        
    def draw(self, debug_mode=False):
        self.instructions_text.draw()
        
    def cleanup(self):
        self.window.flip()
        self.window.flip()
        self.window.flip()
        
        
class TimedInstructionsScreen(InstructionsScreen):
    
    def __init__(self, disp, text, disp_time):
        super(TimedInstructionsScreen, self).__init__(disp, text)
        self.disp_time = disp_time
        
    def draw(self, debug_mode=False):
        self.instructions_text.draw()
        if getAbsTime() - self.t0 > self.disp_time:
            self.move_on_flag.set()
        
        
class ClickInstructionsScreen(InstructionsScreen):
    
    def __init__(self, disp, text, wait_time=1):
        super(ClickInstructionsScreen, self).__init__(disp, text, wait_time=wait_time)
        self.wait_time = wait_time
        if self.wait_time == 0:
            self.continue_button.clickable = True
        
    def draw(self, debug_mode=False):
        self.instructions_text.draw()
        self.continue_button.draw()
        if not self.continue_button.clickable:
            if getAbsTime() - self.t0 > self.wait_time:
                self.continue_button.clickable = True
                
            
class EventInstructionsScreen(InstructionsScreen):
    
    def __init__(self, disp, text, end_event):
        super(EventInstructionsScreen, self).__init__(disp, text)
        self.move_on_flag = end_event
        
    def draw(self, debug_mode=False):
        self.instructions_text.draw()
        
        
class WaitScreen(EventInstructionsScreen):
    
    def __init__(self, disp, text, end_event):
        super(EventInstructionsScreen, self).__init__(disp, text)
        self.move_on_flag = end_event
        self.indicator = Circle(self.window, radius=10)
        self.mouse = Mouse()
        self.ticker = 0
        self.ticker_unit = 2*pi/30
        self.ticker_max = 2*pi
        self.indicator_dist = 15
        
    def draw(self, debug_mode=False):
        self.instructions_text.draw()
        mouse_pos = self.mouse.getPos()
        x = mouse_pos[0] + self.indicator_dist*cos(self.ticker)
        y = mouse_pos[1] + self.indicator_dist*sin(self.ticker)
        self.indicator.pos = (x,y)
        self.indicator.draw()
        self.ticker += self.ticker_unit
        if self.ticker > self.ticker_max:
            self.ticker = 0
            

class DemoScreen(Screen):
    
    def __init__(self, disp, end_event, frame_getter):
        super(DemoScreen, self).__init__(disp)
        self.gaze = Circle(self.window, radius=50)
        self.gaze.fillColor = 'white'
        self.frame_getter = frame_getter
        self.min_time_over = False
        self.end_event = end_event
        
    def draw(self, debug_mode=False):
        frame = self.frame_getter()
        xy = (frame[u'avg'][u'x'],
              frame[u'avg'][u'y'])
        if xy == (0.0,0.0):
            xy = (-5000,-5000)

        self.gaze.pos = self.coords(xy)
        self.gaze.draw()
        
        if self.end_event.is_set():
            self.move_on_flag.set()
        
    def cleanup(self):
        wait(0.5)
        for _ in range(50):
            self.gaze.setRadius(self.gaze.radius - 1)
            self.gaze.draw()
            self.window.flip()
            
            
class ImageScreen(Screen):
    
    
    def __init__(self,
                 disp,
                 text,
                 text_width,
                 image,
                 image_size,
                 text_pos=None,
                 image_pos=None,
                 wait_time=1,
                 extra_image_stims=[]
                 ):
        super(ImageScreen, self).__init__(disp, wait_time=wait_time)
        self.extra_image_stims = extra_image_stims
        self.wait_time = wait_time
        if self.wait_time == 0:
            self.continue_button.clickable = True
        if text_pos is None:
            _text_pos = self.coords(self.width/4, self.height/2)
        else:
            _text_pos = text_pos
        if image_pos is None:
            _image_pos = self.coords(3*self.width/4, self.height/2)
        else:
            _image_pos = image_pos
        self.text_stim = TextStim(
                win=self.window,
                text=text,
                pos=_text_pos,
                height=Screen.default_font_size,
                wrapWidth=text_width
                )
        self.img_stim = ImageStim(
                win=self.window,
                image=image,
                pos=_image_pos,
                size=(image_size[0], image_size[1])
                )
        
    def draw(self, debug_mode=False):
        for img_stim in self.extra_image_stims:
            img_stim.draw()
        self.continue_button.draw()
        self.text_stim.draw()
        self.img_stim.draw()
        
        if not self.continue_button.clickable:
            if getAbsTime() - self.t0 > self.wait_time:
                self.continue_button.clickable = True
        
    def cleanup(self):
        for extra in self.extra_image_stims:
            del extra
        self.window.flip()
        self.window.flip()
        self.window.flip()
        
        
class FlexibleResourcePresentationScreen(Screen):
    
    
    def __init__(self, disp, text, extra_commands, wait_time=1, txt_dict=None, cfg_dict=None):
        super(FlexibleResourcePresentationScreen, self).__init__(disp, wait_time)
        self.txt_dict = txt_dict
        self.cfg_dict = cfg_dict
        self.wait_time = wait_time
        if self.wait_time == 0:
            self.continue_button.clickable = True
        self.text_stim = TextStim(
                win=self.window,
                text=text,
                pos=self.coords((self.x_cfg_2_pix(0.25),
                               self.y_cfg_2_pix(0.5))),
                height=Screen.default_font_size,
                wrapWidth=self.w_cfg_2_pix(0.4)
                )
        self.extra_draw_stims = []
        for command in extra_commands:
            if type(command) == str or type(command) == unicode:
                items = eval(command)
                for item in items:
                    self.extra_draw_stims.append(item)
                
    def draw(self, debug_mode=False):
        if not self.continue_button.clickable:
            if getAbsTime() - self.t0 > self.wait_time:
                self.continue_button.clickable = True
        self.continue_button.draw()
        self.text_stim.draw()
        for stim in self.extra_draw_stims:
            stim.draw()     

    def painfully_clear_example(self, n):
        img = ImageStim(
                win=self.window,
                image='resources/worked_example/Slide{}.PNG'.format(n),
                pos=(0,200),
                size=(960,720)
                )
        background = Rect(
                win=self.window,
                width=img.size[0]+10,
                height=img.size[1]+10,
                fillColor='white',
                lineColor=None,
                pos=img.pos
                )
        return [background, img]

    def mini_contrib_screen(self):
        img = ImageStim(
                win=self.window,
                image='resources/contrib_screen.PNG',
                pos=self.coords((self.x_cfg_2_pix(0.75),
                                 self.y_cfg_2_pix(0.33))),
                size=(960, 540)
                )
        background = Rect(
                win=self.window,
                width=img.size[0]+10,
                height=img.size[1]+10,
                fillColor='white',
                lineColor=None,
                pos=img.pos
                )
        return [background, img]   
        
    def mini_feedback_screen(self, n):
        if FeedbackScreen.reversed:
            img = 'resources/feedback/reversed/Slide{}.PNG'.format(n)
        else:
            img = 'resources/feedback/default/Slide{}.PNG'.format(n)

        image = ImageStim(
                    win=self.window,
                    image=img,
                    pos=self.coords((self.x_cfg_2_pix(0.75),
                                     self.y_cfg_2_pix(0.33))),
                    size=(960, 540)
                    )
        background = Rect(
                win=self.window,
                width=image.size[0]+10,
                height=image.size[1]+10,
                fillColor='white',
                lineColor=None,
                pos=image.pos
                )
        return [background, image]

        
    def cleanup(self):
        self.window.flip()
        self.window.flip()
        self.window.flip()


class KeyboardInputScreen(Screen):
    
    
    def __init__(self, disp, text, input_prompt_list, correct_ans_list=None, extra_draw_list=[]):
        super(KeyboardInputScreen, self).__init__(disp)
        self.instructions_text = TextStim(
                disp, pos=(0, disp.vres*0.2), text=text, height=40,
                wrapWidth=self.w_cfg_2_pix(0.666)
                )
        self.input_prompt_list = []
        self.input_field_list = []
        self.extra_draw_list = extra_draw_list
        height_list = []
        for i in range(len(input_prompt_list)):
            height_list.append(
                    disp.vres*-0.2*i/(len(input_prompt_list)-1)
                    )
        for index, text in enumerate(input_prompt_list):
            self.input_prompt_list.append(TextStim(
                    disp,
                    pos=(disp.hres*-0.2, height_list[index]),
                    text=text,
                    height=40,
                    wrapWidth=disp.hres*0.5
                    ))
            self.input_field_list.append(button.Button(
                    disp,
                    pos=(disp.hres*0.2, height_list[index]),
                    font_size=30,
                    width=disp.hres*0.15,
                    height=40,
                    text_color='black',
                    text=''
                    ))
        self.active_input_field = None
        self.answer_list = []
        self.correct_ans_list = correct_ans_list
            
    def draw(self, debug_mode=False):
        self.continue_button.clickable = True
        key_list = getKeys()
        if self.active_input_field is not None:
            for key in key_list:
                temp = self.active_input_field.text
                if key == 'backspace':
                    if len(temp) > 0:
                        self.active_input_field.text = temp[:-1]
                elif key == 'tab':
                    new_index = self.input_field_list.index(self.active_input_field) + 1
                    try:
                        self.active_input_field = self.input_field_list[new_index]
                    except IndexError:
                        self.active_input_field = self.input_field_list[0]
                elif key in ['1','2','3','4','5','6','7','8','9','0']:
                    self.active_input_field.text = temp + key
                elif key in ['num_0', 'num_1', 'num_4', 'num_7', 'num_2', 'num_5', 'num_8', 'num_3', 'num_6', 'num_9']:
                    self.active_input_field.text = temp + key[-1]
                elif key in ['comma', 'period', 'num_decimal']:
                    self.active_input_field.text = temp + ','
        for index, input_field in enumerate(self.input_field_list):
            if self.mouse.isPressedIn(input_field._frame, [0]):
                self.active_input_field = input_field
            if input_field is self.active_input_field:
                input_field._frame.fillColor = 'white'
            elif input_field._frame.fillColor == 'white':
                input_field._frame.fillColor = 'lightgrey'
        for input_field in self.input_field_list:
            if input_field.text == '':
                self.continue_button.clickable = False
        
                
            
        self.instructions_text.draw()
        self.continue_button.draw()
        for index, input_ in enumerate(self.input_field_list):
            input_.draw()
            self.input_prompt_list[index].draw()
        for item in self.extra_draw_list:
            item.draw()
            
    def cleanup(self):
        self.move_on_flag.clear()
        self.active_input_field = None
        self.window.flip()
        for item in self.input_field_list:
            self.answer_list.append(item.text)
        self.window.flip()
        self.window.flip()
        
#         
# class PainfullyClearInstructions(Screen):
#         
#         
#         def __init__(self, disp):
#             super(PainfullyClearInstructions, self).__init__(disp)
#             
#             self.mypoints = []
#             self.yourpoints = []
#             for x, y in self.gen_points_coords(20, 4, 300, 300):
#                 self.mypoints.append(Circle(
#                         win=self.window, radius=10,
#                         fillColor='white', lineColor=None, pos=(x,y)
#                         ))
#             for x, y in self.gen_points_coords(20, 4, self.width-300-3*30, 300):
#                 self.mypoints.append(Circle(
#                         win=self.window, radius=10,
#                         fillColor='black', lineColor=None, pos=(x,y)
#                         ))
#                 
#         def gen_points_coords(self, n, n_cols, col_1_x, row_1_y):
#             ys = []
#             xs = []
#             for i in range(n):
#                 ys.append(floor((row_1_y + 30*i)/n_cols))
#                 xs.append(col_1_x + 30*(i % n_cols))
#             return zip(xs, ys)
#         
#         def step1(self):
            
                
        
        
        
        
        
        
        
        
        
        
        

        
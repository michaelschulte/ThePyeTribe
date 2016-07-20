'''
Created on Jul 30, 2014

@author: smedema
'''

import yaml

txt_file = 'resources/english/exp_text.txt'
stream2 = file(txt_file)
exp_txt_dict = yaml.load(stream2)
stream2.close()

with open('word.txt', 'w') as file_:
    for i in range(1, 7):
        value_ = exp_txt_dict['instructions_{}'.format(i)]
        str_ = value_.encode('UTF-8')
        file_.write(str_)
    for i in range(1, 4):
        value_ = exp_txt_dict['control_q_{}'.format(i)]
        str_ = value_.encode('UTF-8')
        file_.write(str_)
    value_ = exp_txt_dict['control_q_wrong']
    str_ = value_.encode('UTF-8')
    file_.write(str_)
    for i in range(9):
        value_ = exp_txt_dict['summary_{}'.format(i)]
        str_ = value_.encode('UTF-8')
        file_.write(str_)
    
    value_ = exp_txt_dict['pre_calibration_instructions']
    str_ = value_.encode('UTF-8')
    file_.write(str_)
    
    value_ = exp_txt_dict['detect_pupils_screen']
    str_ = value_.encode('UTF-8')
    file_.write(str_)
    
    value_ = exp_txt_dict['calibration_failed']
    str_ = value_.encode('UTF-8')
    file_.write(str_)
    
    value_ = exp_txt_dict['calibration_failed_again']
    str_ = value_.encode('UTF-8')
    file_.write(str_)
    
    value_ = exp_txt_dict['begin_game_screen_initial']
    str_ = value_.encode('UTF-8')
    file_.write(str_)
    
    value_ = exp_txt_dict['begin_game_screen_subsequent']
    str_ = value_.encode('UTF-8')
    file_.write(str_)
    
    value_ = exp_txt_dict['final_screen']
    str_ = value_.encode('UTF-8')
    file_.write(str_)
    
print 'done'

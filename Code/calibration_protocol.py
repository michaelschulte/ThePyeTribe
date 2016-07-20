'''
Created on Jul 29, 2014

@author: smedema
'''

import screens

def calibrate(window, et_server, exp_txt_dict, exp_cfg_dict, debug_mode=False):
    '''
    This is the calibration block. If we are in debug mode, no need
    to redo the calibration if we have one already, so we try to
    get an existing one and return that.
    
    Otherwise, we attempt calibration 3 times. If even the third
    time fails, we just continue the experiment so that we can at
    least get data on one subject.
    '''
    window.flip()
    if debug_mode:
        if et_server.iscalibrated:
            calibresult = et_server.calibresult
            if calibresult[u'result']:
                return calibresult
    else:
        et_server.clear_calibration()
        
    screens.TimedInstructionsScreen(
                disp=window, disp_time=2.5,
                text=exp_txt_dict[u'calibration_look']
                ).run()
    calib = window.calibrate(et_server)
                                            
    if calib[u'result']:
        return calib
    else:
        screens.ClickInstructionsScreen(
                    disp=window, wait_time=2,
                    text=exp_txt_dict[u'calibration_failed']
                    ).run()
        screens.TimedInstructionsScreen(
                disp=window, disp_time=2.5,
                text=exp_txt_dict[u'calibration_look']
                ).run()
        calib = window.calibrate(et_server)
            
    if calib[u'result']:
        return calib
    else:
        screens.ClickInstructionsScreen(
                disp=window, wait_time=2,
                text=exp_txt_dict[u'calibration_failed_again']
                ).run()
        screens.DetectPupilsScreen(
                disp=window, config_dict=exp_cfg_dict,
                text=exp_txt_dict[u'detect_pupils_screen'],
                pupil_coords_getter=et_server.get_pupil_locations,
                seconds_to_ok=exp_cfg_dict[u'detect_pupils_screen'][u'seconds_to_ok']
                ).run()
        screens.TimedInstructionsScreen(
                disp=window, disp_time=2.5,
                text=exp_txt_dict[u'calibration_look']
                ).run()
        calib = window.calibrate(et_server)
        
    return calib
'''
Created on Jul 21, 2014

@author: smedema
'''

import threading
from time import sleep
from Queue import Queue
from datetime import datetime


class PublicGoodsGame(object):
    
    
    def __init__(
            self, 
            num_rounds,
            num_players,
            total_multiplier,
            endowment,
            IP2num_dict,
            contrib_screen,
            all_contributions_in,
            wait_screen,
            feedback_screen,
            blank_screen,
            contrib_file_name,
            handler_communicator
            ):
        self.num_rounds = num_rounds
        self.num_players = num_players
        self.total_multiplier = total_multiplier
        self.endowment = endowment
        self.IP2num_dict = IP2num_dict
        self.contrib_file_name = contrib_file_name
        self.handler_comm = handler_communicator
        
        self.all_contributions_in = all_contributions_in
        self.contribution_q = Queue()
        self.total_payoff = 0
        
        self.contrib_screen = contrib_screen
        self.wait_screen = wait_screen
        self.feedback_screen = feedback_screen
        self.blank_screen = blank_screen

    def run(self, previous_rounds, game_number=None):
        for which_round in range(1, self.num_rounds+1):
            print('Round {}'.format(which_round))

            contr_onset = datetime.now().isoformat(' ')
            self.contrib_screen.run()
            contr_off = datetime.now().isoformat(' ')
            self.blank_screen.run()
            
            self.handler_comm.report_contribution(int(self.contrib_screen.contrib_choice))
            threading.Thread(
                    target=self.wait_on_contributions,
                    args=(previous_rounds+which_round,)
                    ).start()
            self.wait_screen.run()
            self.all_contributions_in.clear()
            self.blank_screen.run()
            contrib_dict = self.contribution_q.get()
            my_payoff = self.calculate_feedback_and_update(contrib_dict)
            self.total_payoff += my_payoff
            
            summary_onset = datetime.now().isoformat(' ')
            self.feedback_screen.run()
            summary_off = datetime.now().isoformat(' ')
            self.blank_screen.run()
            
            other_contrib_ls = [None]*(self.num_players)
            for IP, value_ in contrib_dict.iteritems():
                other_contrib_ls[self.IP2num_dict[IP]] = value_
                    
            other_contrib_str = ''
            for index, contrib in enumerate(other_contrib_ls):
                if index == 0:
                    continue
                else:
                    other_contrib_str = other_contrib_str + '{}, '.format(contrib)
            
            with open(self.contrib_file_name, 'a') as contribs:
                contribs.write('{}, {}, {}, {}{}, {}, {}, {}, {}\n'.format(
                        game_number,
                        which_round,
                        self.contrib_screen.contrib_choice,
                        other_contrib_str,
                        my_payoff,
                        contr_onset,
                        contr_off,
                        summary_onset,
                        summary_off
                        ))
        
    
    def calculate_feedback_and_update(self, contr_dict):
        '''
        This is where we actually calculate the results of each round. 
         
        We need a dictionary of contributions whose keys are the IP
        addresses of the computers from which each contribution was
        made.
        '''
        contr_sum = 0
        for _, contr in contr_dict.iteritems():
            contr_sum += contr
        contr_avg = contr_sum/(self.num_players*1.0)
        bonus = self.total_multiplier*contr_sum/self.num_players
        payoff_sum = 0
        payoff_dict = {}
        for IP, contr in contr_dict.iteritems():
            payoff_dict[IP] = self.endowment - contr + bonus
            payoff_sum += payoff_dict[IP]
            
        payoff_avg = payoff_sum/self.num_players*1.0
        
        other_contr = [None]*(self.num_players-1)
        other_payoff = [None]*(self.num_players-1)
        for IP, num in self.IP2num_dict.iteritems(): 
            if num == 0:
                my_contr = contr_dict[IP]
                my_payoff = payoff_dict[IP]
            else:
                other_contr[num-1] = contr_dict[IP]
                other_payoff[num-1] = payoff_dict[IP]
        
        self.feedback_screen.update_info(
                contr_avg, payoff_avg, contr_sum, payoff_sum, my_contr,
                my_payoff, other_contr, other_payoff
                )
        return my_payoff
    
    def wait_on_contributions(self, len_needed):
        sleep(1.750)
        contrib_dict = {}
        while contrib_dict == {}:
            sleep(0.250)
            contrib_dict = self.handler_comm.get_value(u'all_contributions')
            for IP, list_ in contrib_dict.iteritems():
                if len(list_) < len_needed:
                    contrib_dict = {}
                    break
                else:
                    contrib_dict[IP] = list_[-1]
        self.contribution_q.put(contrib_dict)
        self.all_contributions_in.set()
    


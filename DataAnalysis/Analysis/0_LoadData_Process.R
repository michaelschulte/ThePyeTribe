# EYE Games
# Michael Schulte-Mecklenbeck & Tomas Lejarraga 
# Analysis for Lejarraga, T., Schulte-Mecklenbeck, M., & Smedema, D. (submitted). Simultaneous Eye-Tracking for Economic Games. Behavior Research Methods. 

# clean slate
rm(list = ls())

# change your working directory path to the folder of this file!! 
setwd('~/Dropbox (2.0)/9_AbschgeschlosseneProjekte/EyeGamessubmission_BRM/GithubRepo/Analysis')

# some libraries we might need
require(dplyr)
require(stringr)

# LOAD Eye-tracking -----
# set data directory
  setwd('../RawData/eyetracking/')
# get list of filesnames in /data directory
  filenames <- list.files(pattern="*.*")
# read all files in the filenames into a list
  myfiles <- lapply(filenames, read.table, header=TRUE, sep=',')
# add filenames to each dataframe in the list
  myfiles <- mapply(cbind, myfiles, "filename"=filenames, SIMPLIFY=F)
# extract the list items into a dataframe
# 40 VPN * 30 Trials 
  rawET <- do.call(rbind.data.frame, myfiles)
# split up participant number 
  rawET$ID <- as.character(str_match_all(as.character(rawET$filename), '[0-9]+_[0-9]+'))
# trim whitespace in AOI 
  rawET$AOI <- str_trim(as.character(rawET$AOI))
# split up round number 
  rawET$player_in_round <- as.character(str_match_all(as.character(rawET$filename), '_[0-9]'))
  rawET$player_in_round <- str_replace(rawET$player_in_round, '_', '')  
# check for participant with empty eye tracking data
  check_empty <- rawET[rawET$final_AOI_fix == ' None',]
  
  no_data <- check_empty %>%
             group_by(ID) %>%
             summarise(l = length(ID))%>%
             filter(l == 30)

# housekeeping
  remove(filenames, myfiles)
# saveRDS rawETdata file
  saveRDS(rawET, file='../../Data/ET_raw.RDS')

# LOAD Behavioral ----
# set data directory
  setwd('../behavioral/')
# get list of filesnames in /data directory
  filenames <- list.files(pattern="*.txt")
# read all files in the filenames into a list
  myfiles <- lapply(filenames, read.table, header=TRUE, sep=',')
# extract the list items into a dataframe
# 40 VPN * 30 Trials = 1200 Lines
  raw <- do.call(rbind.data.frame, myfiles)
# extract participant number and player number
  part_number <- str_extract(filenames,'([0-9]+_[0-9]+)')
# replicate participant numbers for 30 trials each and write into raw
  raw$ID <- rep(part_number, each = 30)
# split up participant number and player number 
  raw$player_in_round <- strsplit(raw$ID, split = "_")
# overwrite ID
  raw$player_in_round <- sapply(raw$player_in_round,function(x) x[2])
# move into something useful 
  rawB <- raw
# add global ID 
  rawB$participant <- (paste(rawB$ID,rawB$player_in_round,sep=''))
# housekeeping
  remove(filenames, myfiles)
# saveRDS rawdata file
  saveRDS(rawB, file='../../Data/Behavioral_raw.RDS')

# LOAD Demography -----
  demographics <- read.csv(file = '../demographics.txt', sep = ',')
  # trim whitespace in sex 
  demographics$sex <- str_trim(as.character(demographics$sex))
  # saveRDS rawdata file
  saveRDS(demographics, file='../../Data/Demographics.RDS')
  
# LOAD Contributions ----
  
# generate smaller dataframe without timing info
  contributions <- subset(rawB, select = c('participant','ID','player_in_round','game','round','contribution','opponent_1_contrib','payoff'))

# rename ID column 
  contributions$pair_in_game <- contributions$ID
  contributions$ID <- NULL

# classify contributions

    # add difference measure on contributions
      contributions$c_diff <- with(contributions, contribution - opponent_1_contrib)
    # classify differences
      contributions$c_class <- ifelse(contributions$c_diff == 0, 'equal', 
                             ifelse(contributions$c_diff > 0, 'more than other', 
                             ifelse(contributions$c_diff < 0, 'less than other', NA
                             )))

# saveRDS rawdata file
  saveRDS(contributions, file='../../Data/Contributions.RDS')

  
# PROCESS data ET ----
# apparently there are acquisitions of length 'None' in the file - lets remove them
  rawETdata <- rawET[!rawET$final_AOI_fix == ' None',]
# convert characters in number 
  rawETdata$begin_AOI_fix <- as.numeric(rawETdata$begin_AOI_fix)
  rawETdata$final_AOI_fix <- as.numeric(rawETdata$final_AOI_fix)
# calculate fixation length 
  rawETdata$fixlength <- with(rawETdata, final_AOI_fix - begin_AOI_fix)

# cut very short acquisitions (smaller than 50 ms)
  ET50 <- rawETdata[rawETdata$fixlength > 49,]
# cleaning at bottom and top
  meanFix <- mean(ET50$fixlength)
  sdFix <- sd(ET50$fixlength)
# cut larger than 3 SDs over median
  ET50 <- ET50[ET50$fixlength < meanFix + 2*sdFix,]
  
# PROCESS add AOI labels ----
# C: Contribution, L: Label, P: Payoff
# load labels    
  AOI_labels <- read.table(file='../AOI_description.txt', header = TRUE, sep = ',', as.is = TRUE)
# merge into dataframe
  ET50 <- merge(ET50, AOI_labels, by="AOI", all=TRUE)
  ET50 <- arrange(ET50,ID,game,round,player_in_round,ID,AOI_Label,AOI_Category)

# saveRDS ratio df
saveRDS(ET50, file = '../../Data/ET50.RDS')

# generate summay file
# C: Contribution / P: Payoff
  ET50Fix <- ET50 %>%
                filter(AOI_Category == 'C' | AOI_Category == 'P') %>%
                filter(AOI_Label %in% c("You","PersonB","Sum","Avg")) %>%
                group_by(ID,game,round,AOI_Label,AOI_Category) %>%
                summarise(
                          fix_length = sum((fixlength))
                         ) 

# build full dataset pattern to account for non-acquired cells: 8*10*3*20 = 4800 rows
  completeDF <- data.frame(participant = rep(unique(ET50Fix$ID), each = 120, time = 1),
                           game = rep(1:3, each = 80, times = 1), 
                           round = rep(1:10, each = 8, times = 1), 
                           AOI_Label = rep(1:4, each = 2, times = 1), 
                           AOI_Category = rep(1:2, times = 4)
                           )
           completeDF <- group_by(completeDF, participant,game,round,AOI_Label,AOI_Category)
# recode variables
  completeDF$AOI_Label <- ifelse(completeDF$AOI_Label == 1, "You",
                          ifelse(completeDF$AOI_Label == 2, "PersonB",
                          ifelse(completeDF$AOI_Label == 3, "Sum",
                          ifelse(completeDF$AOI_Label == 4, "Avg",NA))))
  # C: Contribution / P: Payoff
  completeDF$AOI_Category <- ifelse(completeDF$AOI_Category == 1, "C",
                             ifelse(completeDF$AOI_Category == 2, "P",NA))

  ET50complete  <- merge(ET50Fix, completeDF, all.y = TRUE)

# calculate ratio of fixation time between contribution and payoff
  ET50ratioFix <- ET50complete %>%
                group_by(participant, game, round, AOI_Label, AOI_Category) %>%
                summarise(fixation = sum(fix_length, na.rm = TRUE)) %>%
                mutate(ratio = fixation / lag(fixation))

# saveRDS ratio df
saveRDS(ET50ratioFix, file = '../../Data/ET50ratioFix.RDS')


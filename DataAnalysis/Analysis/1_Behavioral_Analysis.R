# EYE Games - Modeling of individual contributions
# Tomas Lejarraga & Michael Schulte-Mecklenbeck  
# Analysis for Lejarraga, T., Schulte-Mecklenbeck, M., & Smedema, D. (submitted). Simultaneous Eye-Tracking for Economic Games. Behavior Research Methods. 

# set everything clean
 rm(list = ls())
# 
# # change your working directory path to the folder of this file!! 
 setwd('~/Dropbox (2.0)/9_AbschgeschlosseneProjekte/EyeGamessubmission_BRM/GithubRepo/Analysis')
# 
# 
# # Load packages
 library(stringr)
 library(ggplot2)
 library(reshape)
 library(reshape2)
 
# laod cotribution data
raw <- readRDS('../data/Contributions.RDS')

# Models from Fischbacher & Gächter (2010)
# All models are built under the assumption that people use two "modules": First form beliefs about the opponent and then decide how much to contribute.

# Naïve beliefs
raw$belief_naive <- 0
for(i in 1:length(raw$belief_naive)) {
  raw$belief_naive[i] <- ifelse(raw$round[i] == 1, NA, raw$opponent_1_contrib[i - 1])
}

# Actual beliefs
raw$belief_actual <- 0
for(i in 1:length(raw$belief_actual)) {
  raw$belief_actual[i] <- ifelse(raw$round[i] == 1, NA, 
                                 ifelse(raw$round[i] == 2, raw$opponent_1_contrib[i - 1],
                                        0.118 + 0.415*raw$opponent_1_contrib[i - 1] + 0.569*raw$belief_actual[i - 1]))
}

# pCCn (perfect Conditional Cooperator with naive beliefs). Note: This model makes no predictions for round 1 of each game. 
raw$pCCn_contribution <- raw$belief_naive

# pCCa (pCC with "actual" beliefs estimated by a regression model, displayed in Table 1, model 3, page 548)
raw$pCCa_contribution <- raw$belief_actual

# iCCn (identical Conditional Cooperator with naive beliefs). Note: The identical cooperation follows a linear model of the form: a + k*belief (p. 552)
raw$iCCn_contribution <- 0.956 + 0.425*raw$belief_naive

# iCCa (iCC with actual beliefs)
raw$iCCa_contribution <- 0.956 + 0.425*raw$belief_actual

# aCCa ("Actual" Conditional Cooperator with "actual" beliefs taken from in pCCa. The tendency to cooperate is taken from Table 2, model 3, page 549)
# aCCn ("Actual" Conditional Cooperator with Naive beliefs)
# These models cannot be estimated because they rely on a variable that we did not measure: "predicted cooperation".

# Matching model (using 0.5 as a default averaging rule)
w <- 0.5
raw$matching_0.5_contribution <- 0 
for(i in 1:length(raw$matching_0.5_contribution)) {
  raw$matching_0.5_contribution[i] <- ifelse(raw$round[i] == 1, NA, 
                                         ifelse(raw$round[i] == 2, w*raw$contribution[i - 1] + (1 - w)*raw$opponent_1_contrib[i - 1],
                                                w*raw$matching_0.5_contribution[i - 1] + (1 - w)*raw$opponent_1_contrib[i - 1]))
}


# Edit for plotting
contribution_median <- aggregate(raw$contribution, by = list(raw$game, raw$round), median)
colnames(contribution_median) <- c("game", "round", "contribution_median")
pCCn_contribution_median <- aggregate(raw$pCCn_contribution, by = list(raw$game, raw$round), median)
colnames(pCCn_contribution_median) <- c("game", "round", "pCCn_contribution_median")
pCCa_contribution_median <- aggregate(raw$pCCa_contribution, by = list(raw$game, raw$round), median)
colnames(pCCa_contribution_median) <- c("game", "round", "pCCa_contribution_median")
iCCn_contribution_median <- aggregate(raw$iCCn_contribution, by = list(raw$game, raw$round), median) 
colnames(iCCn_contribution_median) <- c("game", "round", "iCCn_contribution_median")
iCCa_contribution_median <- aggregate(raw$iCCa_contribution, by = list(raw$game, raw$round), median)
colnames(iCCa_contribution_median) <- c("game", "round", "iCCa_contribution_median")
matching_0.5_contribution_median <- aggregate(raw$matching_0.5_contribution, by = list(raw$game, raw$round), median)
colnames(matching_0.5_contribution_median) <- c("game", "round", "matching_0.5_contribution_median")

# Drop "i" models
contributions_median <- merge(contribution_median, pCCn_contribution_median)
contributions_median <- merge(contributions_median, pCCa_contribution_median)
contributions_median <- merge(contributions_median, matching_0.5_contribution_median)
contributions_median <- melt(contributions_median, id = c("game", "round"))

# Housekeeping 
rm(contribution_median, pCCn_contribution_median, pCCa_contribution_median, iCCn_contribution_median, iCCa_contribution_median, matching_0.5_contribution_median)

# Plot aggregate model predictions
ggplot(contributions_median, aes(x = round, y = value, colour = variable)) + 
  geom_line() +
  scale_x_continuous(breaks = 1:10) + 
  scale_colour_brewer(palette = 'Set1')  +
  xlab('Round') +
  ylab('Contribution') +
  facet_grid(game ~ .) +
  ylim(0, 20)

# Plot individual matching_0.5_model predicitons
contributions_individual <- subset(raw, game == 1) # Fix by hand
ggplot(contributions_individual, aes(x = round, y = contribution)) + 
  geom_line() +
  geom_line(data = contributions_individual, aes(x = round, y = matching_0.5_contribution), col = "red") +
  scale_x_continuous(breaks = 1:10) + 
  scale_colour_brewer(palette = 'Set1')  +
  xlab('Round') +
  ylab('Contribution') +
  facet_grid(id ~ .) +
  ylim(0, 20) +
  ggtitle("Matching_0.5 predictions")

# Evaluation of models
pCCn_msd <- mean((raw$contribution - raw$pCCn_contribution)^2, na.rm = TRUE)
pCCa_msd <- mean((raw$contribution - raw$pCCa_contribution)^2, na.rm = TRUE)
matching_0.5_msd <- mean((raw$contribution - raw$matching_0.5_contribution)^2, na.rm = TRUE)
rbind(pCCn_msd, pCCa_msd, matching_0.5_msd)

# Fit matching model to each individual

fit_data <- subset(raw, game == 1) # Fit to specific game

subject <- function(s) {
  ind <- subset(fit_data, id == s[1]) #fit model to participant
  matching_model <- function(w) {
    w <- w[1]
    ind$matching_contribution <- 0 
    for(i in 1:length(ind$matching_contribution)) {
      ind$matching_contribution[i] <- ifelse(ind$round[i] == 1, NA, 
                                             ifelse(ind$round[i] == 2, w*ind$contribution[i - 1] + (1 - w)*ind$opponent_1_contrib[i - 1],
                                                    w*ind$matching_contribution[i - 1] + (1 - w)*ind$opponent_1_contrib[i - 1]))
    }
    msd <- mean((ind$contribution - ind$matching_contribution)^2, na.rm = TRUE)
    msd
  }
  
  grid <- expand.grid(seq(0, 1, by = .01))
  tgrid <- data.frame(t(grid))
  result <- lapply(tgrid, matching_model)
  res <- t(rbind(result, tgrid))
  colnames(res) <- list("msd", "w")
  res[which.min(res[,"msd"] ),]
    
}
grid <- expand.grid(unique(fit_data$id))  #Expands a grid with all subject id's available in the choice dataframe
tgrid <- data.frame(t(grid))
result <- lapply(tgrid, subject)
res <- data.frame(t(data.frame(result)))
res <- cbind(grid, res)
colnames(res) <- c("id", "msd", "w")

ggplot(data = res, aes(x = w)) +
  geom_histogram() +
  xlab("Anchor on own previous contribution (w)") +
  theme(panel.background = element_blank()) +
  theme(text = element_text(size = 15)) +
  theme(legend.title = element_blank()) +
  theme(legend.key = element_blank()) +
  theme(legend.background = element_blank()) +
  theme(panel.background = element_rect(colour = "grey")) +
  ggtitle("Matching model")

ggplot(data = res, aes(x = msd)) +
  geom_histogram() +
  #xlab("Anchor on own previous contribution (w)") +
  theme(panel.background = element_blank()) +
  theme(text = element_text(size = 15)) +
  theme(legend.title = element_blank()) +
  theme(legend.key = element_blank()) +
  theme(legend.background = element_blank()) +
  theme(panel.background = element_rect(colour = "grey")) +
  ggtitle("Matching model")

# Generate predictions for each individual
fit_data <- merge(fit_data, res)
names(fit_data)[names(fit_data) == "w"] <- "matching_w"
fit_data$msd <- NULL 
fit_data$matching_contribution <- 0 
for(i in 1:length(fit_data$matching_contribution)) {
  fit_data$matching_contribution[i] <- ifelse(fit_data$round[i] == 1, NA, 
                                         ifelse(fit_data$round[i] == 2, fit_data$matching_w[i]*fit_data$contribution[i - 1] + (1 - fit_data$matching_w[i])*fit_data$opponent_1_contrib[i - 1],
                                                fit_data$matching_w[i]*fit_data$matching_contribution[i - 1] + (1 - fit_data$matching_w)[i]*fit_data$opponent_1_contrib[i - 1]))
}

matching_msd <- mean((fit_data$contribution - fit_data$matching_contribution)^2, na.rm = TRUE)

# Plot individual matching model predicitons
ggplot(fit_data, aes(x = round, y = contribution)) + 
  geom_line() +
  geom_line(data = fit_data, aes(x = round, y = matching_contribution), col = "red") +
  scale_x_continuous(breaks = 1:10) + 
  scale_colour_brewer(palette = 'Set1')  +
  xlab('Round') +
  ylab('Contribution') +
  facet_grid(id ~ .) +
  ylim(0, 20) +
  ggtitle("Matching model predictions")

# Plot aggregate model predictions including fitted matching model
matching_contribution_median <- aggregate(fit_data$matching_contribution, by = list(fit_data$game, fit_data$round), median)
colnames(matching_contribution_median) <- c("game", "round", "matching_contribution_median")
contributions_median <- subset(contributions_median, game == 1)
matching_contribution_median <- melt(matching_contribution_median, id = c("game", "round"))
contributions_median <- rbind(contributions_median, matching_contribution_median)

ggplot(contributions_median, aes(x = round, y = value, colour = variable)) + 
  geom_line() +
  scale_x_continuous(breaks = 1:10) + 
  scale_colour_brewer(palette = 'Set1')  +
  xlab('Round') +
  ylab('Contribution') +
  #facet_grid(game ~ .) +
  ylim(0, 20)


# Load distribution of attention
load("/Volumes/LejarragaTomas/Eye games/0_PilotExperiment/1_Analysis/data/ET50_allAOIs.Rdata")
attention <- ET50

# Calculate relative attention (ra) using a ratio and a logistic rule
attention <- cast(attention, ID + round ~ AOI_Label)
attention$PersonB <- ifelse(is.na(attention$PersonB) == TRUE, 0, attention$PersonB)
attention$You <- ifelse(is.na(attention$You) == TRUE, 0, attention$You)
attention$ra_r <- attention$You/(attention$You + attention$PersonB)

# Correlate w with ra
ra <- aggregate(attention$ra_r, by = list(attention$ID), mean)
colnames(ra) <- c("id", "mean_ra_r")
ra <- merge(res, ra)
cor.test(ra$mean_ra_r, ra$w)

ggplot(ra, aes(x = mean_ra_r, y = w)) +
  geom_point() +
  geom_smooth(method= lm, colour = "grey") +
  xlab("Relative attention (ra)") +
  ylab("Weight given to previous own contribution (w)") +
  ylim(0, 1) +
  theme_bw() +
  theme(panel.grid.major = element_blank(),
        panel.grid.minor = element_blank())
#ggsave("~/Dropbox/EyeGames - Michael & Daniel/0_PilotExperiment/1_Analysis/graphs/correlation_attention_w.pdf", width = 6, height = 6, units = "in", dpi = 300)  # Tomás path

# Plot relative attention by pairs
attention$pair_id <- as.numeric(gsub( "_.*$", "", attention$ID))
attention$player_id_within_pair <- sub(".*_", "", attention$ID)
pairs <- c("Pair 2", "Pair 5", "Pair 10", "Pair 12")
labels <- function(variable,value){
  return(pairs[value])
}

ggplot(subset(attention, pair_id == 2 | pair_id == 5 | pair_id == 10 | pair_id == 12), aes(x = round, y = ra_r, colour = player_id_within_pair)) + 
  geom_line() +
  scale_x_continuous(breaks = 1:10) + 
  scale_colour_brewer(palette = 'Set1')  +
  xlab('Round') +
  ylab('Relative attention') +
  facet_grid(pair_id ~ ., , labeller = as_labeller(labels)) +
  ylim(0, 1) +
  theme_bw() +
  theme(panel.grid.major = element_blank(),
        panel.grid.minor = element_blank(),
        text = element_text(size = 15),
        legend.title = element_blank(),
        legend.key = element_blank(),
        legend.background = element_blank(),
        legend.position="none",
        panel.background = element_rect(colour = "grey"))


# Calculate difference in relative attention
attention <- subset(attention, select = c("ID", "round", "ra_r", "pair_id", "player_id_within_pair"))
attention <- dcast(attention, pair_id + round ~ player_id_within_pair, value.var="ra_r")
attention[,5] <-NULL
attention <- na.omit(attention)
colnames(attention) <- c("pair_id", "round", "ra_1", "ra_2")

attention$diff_ra <- attention$ra_1 - attention$ra_2

# Calculate difference in contributions
contributions <- subset(contributions_individual, select = c("game", "round", "pair_id", "player_id_within_pair", "contribution"))
contributions <- dcast(contributions, pair_id + round ~ player_id_within_pair, value.var="contribution")
colnames(contributions) <- c("pair_id", "round", "contribution_1", "contribution_2")

contributions$diff_1 <- contributions$contribution_1 - contributions$contribution_2
contributions$diff_2 <- contributions$contribution_2 - contributions$contribution_1

contributions <- contributions[order(contributions$pair_id, contributions$round),]
contributions$prev_diff_1 <- NA
for(i in 1:length(contributions$prev_diff_1)) {
  contributions$prev_diff_1[i] <- ifelse(contributions$round[i] == 1, NA, contributions$diff_1[i - 1])}
contributions$prev_diff_2 <- NA
for(i in 1:length(contributions$prev_diff_2)) {
  contributions$prev_diff_2[i] <- ifelse(contributions$round[i] == 1, NA, contributions$diff_2[i - 1])}

# Plot difference in ra as a function of difference in contribution in the previous round 
relative <- merge(attention, contributions)

pl1 <- subset(relative, select = c("ra_1", "prev_diff_1"))
pl2 <- subset(relative, select = c("ra_2", "prev_diff_2"))
colnames(pl1) <- c("ra", "prev_diff")
colnames(pl2) <- c("ra", "prev_diff")
relative <- rbind(pl1, pl2)

ggplot(relative, aes(x = prev_diff, y = ra)) + 
  geom_jitter(colour = "black", alpha = 0.5) +
  geom_smooth(method = "lm", se = FALSE, size = .5, colour = "black") +
  xlab('Difference in contributions in previous round (self - other)') +
  ylab('Relative attention') +
  ylim(0, .7) +
  xlim(-20, 20) +
  theme_bw() +
  theme(panel.grid.major = element_blank(),
        panel.grid.minor = element_blank(),
        text = element_text(size = 15),
        legend.title = element_blank(),
        legend.key = element_blank(),
        legend.background = element_blank(),
        legend.position="none",
        panel.background = element_rect(colour = "grey"))


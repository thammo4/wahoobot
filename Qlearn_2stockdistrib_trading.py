import time; start_time = time.perf_counter();

import itertools;
import numpy as np;

#
# Define relevant constants
#

# EPISODE_COUNT 		= 5000;
EPISODE_COUNT 		= 2500;
DAYS_PER_EPISODE 	= 50;
ACCT_BAL_0 			= 1000;

SHARES_PER_TRADE = 10; # buy/sell fixed number of shares each time for simplicity

actions = ('hold', 'buy', 'sell');
ACTIONS = list(itertools.product(actions, range(SHARES_PER_TRADE+1), repeat=2));
ACTIONS = [action for action in ACTIONS if sum(action[1:2]) <= SHARES_PER_TRADE];


#
# Define greek hyperparameters: random-action-rate, learning-rate, discount-rate
#

EPSILON = .175;
ALPHA = .150;
GAMMA = .925;


#
# Initialize state space, action space, and Q-table
#

# state_count_A = 500;
# state_count_B = 500;
state_count_A, state_count_B = 100, 100;

action_count_A = 3;
action_count_B = 3;

# action_count = action_count_A * action_count_B;
action_count = len(ACTIONS);

Q = np.zeros((state_count_A, state_count_B, action_count));



#
# Simulate daily closing price by evaluating f(theta) = 4sin(theta) + 25 for a specified theta (e.g. day)
# Stock XYZ
#

def closing_price_A (theta):
	noise = 0;
	random_value = np.random.rand();
	if random_value <= .250:
		noise = 2*np.random.standard_t(1,1)[0];
	elif random_value > .250 and random_value <= .750:
		noise = np.random.standard_cauchy(1)[0];
	elif random_value > .750:
		noise = np.random.gamma(4.25,1,1)[0];
	if np.abs(noise) > 25:
		noise *= .250;
	return (12*np.sin(.3*theta)+25) + noise;


#
# Simulate daily closing price by evaluating f(theta) = 25cos(.5*theta) + 35 for specified theta (e.g day)
#

def closing_price_B (theta):
	noise = 0;
	random_value = np.random.rand();
	if random_value <= .50:
		noise = np.random.poisson(8,1)[0];
	else:
		noise = np.random.rayleigh(5);
	if np.random.rand() <= .725:
		noise *= -1;
	return (25*np.cos(.5*theta)+35) + noise;


#
# Define epsilon-greedy policy implementation (e.g. map: states -> actions)
#

def choose_action (state_A, state_B):
	if np.random.rand() < EPSILON:
		print('********************************* RANDOM ACTION ***********************************');
		return np.random.choice(len(ACTIONS));
	else:
		return np.argmax(Q[state_A, state_B, :]);



#
# Define function to determine the (next state, reward) when given (current state, action)
#

def execute_action (state_A, state_B, action_idx, shares_A, shares_B, bal):
	action_A, shares_trade_A, action_B, shares_trade_B = ACTIONS[action_idx]; # ex: ('sell', 1, 'buy', 6)

	next_day_price_A = closing_price_A(state_A+1);
	next_day_price_B = closing_price_B(state_B+1);

	#
	# Define action for Stock A
	#

	if action_A == 'buy' and bal >= next_day_price_A * shares_trade_A:
		shares_A += shares_trade_A;
		bal -= next_day_price_A*shares_trade_A;
	elif action_A == 'sell' and shares_A >= shares_trade_A:
		shares_A -= shares_trade_A;
		bal += next_day_price_A * shares_trade_A;

	#
	# Define action for Stock B
	#

	if action_B == 'buy' and bal >= next_day_price_B * shares_trade_B:
		shares_B += shares_trade_B;
		bal -= next_day_price_B * shares_trade_B;
	elif action_B == 'sell' and shares_B >= shares_trade_B:
		shares_B -= shares_trade_B;
		bal += next_day_price_B * shares_trade_B;

	#
	# Define next state for Stocks A, B
	#

	next_state_A = (state_A +1) % state_count_A;
	next_state_B = (state_B +1) % state_count_B;

	#
	# Account value is weighted combination of shares and price
	#

	next_acct_value = bal + shares_A*next_day_price_A + shares_B*next_day_price_B;

	#
	# Compute reward relative to starting balance
	#

	reward = next_acct_value - ACCT_BAL_0;

	return {
		'next_state_A' 	: next_state_A,
		'next_state_B' 	: next_state_B,
		'shares_A' 		: shares_A,
		'shares_B' 		: shares_B,
		'bal' 			: bal,
		'reward' 		: reward
	};



#
# Train Agent
#

for ep in range(EPISODE_COUNT):
	state_A = ep * DAYS_PER_EPISODE % state_count_A;
	state_B = ep * DAYS_PER_EPISODE % state_count_B;

	acct_bal = ACCT_BAL_0;

	shares_held_A = 0;
	shares_held_B = 0;

	for day in range(DAYS_PER_EPISODE):
		action_index = choose_action(state_A, state_B);
		action_outcome = execute_action(state_A, state_B, action_index, shares_held_A, shares_held_B, acct_bal);

		print('priceA = ', closing_price_A(state_A));
		print('priceB = ', closing_price_B(state_B));

		next_state_A = action_outcome['next_state_A']; 	print('nextA = ', next_state_A);
		next_state_B = action_outcome['next_state_B']; 	print('nextB = ', next_state_B);
		shares_held_A = action_outcome['shares_A']; 	print('sharesA = ', shares_held_A);
		shares_held_B = action_outcome['shares_B']; 	print('sharesB = ', shares_held_B);
		reward = action_outcome['reward']; 				print('reward = ', reward);
		acct_bal = action_outcome['bal']; 				print('account balance = ', acct_bal);


		#
		# Define terminal condition (e.g. ran out of money)
		#

		if acct_bal <= 0:
			print('!!!!!! BANKRUPT WTF ??????????');
			break;

		#
		# Update Q-table per Q-learning update rule
		#

		print('update entry for (state_A, state_B, action) = (', state_A, ', ', state_B, ', ', action_index, ') -> ', np.max(Q[next_state_A, next_state_B, :]));

		Q[state_A, state_B, action_index] += ALPHA * (reward + GAMMA * np.max(Q[next_state_A, next_state_B, :]) - Q[state_A, state_B, action_index]);

		state_A, state_B = next_state_A, next_state_B;
		print('Q\n', Q);

		print('-------------');
		print('\n');




#
# Define testing environment for learned agent
#

def test_agent (Q_table, state0_A, state0_B, shares0_A, shares0_B, bal0, max_iterations=1e4):
	state_A, state_B = state0_A, state0_B;
	shares_A, shares_B = shares0_A, shares0_B;

	bal = bal0;
	total_reward = 0;

	iter = 0;
	while True:
		action 			= np.argmax(Q_table[state_A, state_B, :]);
		action_outcome 	= execute_action(state_A, state_B, action, shares_A, shares_B, bal);

		next_state_A 	= action_outcome['next_state_A'];
		shares_A 		= action_outcome['shares_A'];

		next_state_B 	= action_outcome['next_state_B'];
		shares_B 		= action_outcome['shares_B'];

		bal 	= action_outcome['bal'];
		reward 	= action_outcome['reward'];

		total_reward += reward;

		state_A, state_B = next_state_A, next_state_B;

		#
		# Terminal condition for intra-episode iterations
		#

		if bal <= 0 or iter == int(max_iterations):
			break;

		iter += 1;

	return {'total_reward':total_reward, 'acct_bal':bal, 'shares':(shares_A, shares_B)};




#
# Test agent
# 	• Iterate over states: state0,...,state_terminal
# 	• At each state, determine action by indexing Q-table row and identifying the column with the largest Q-value (e.g. cumulative discounted total reward)
# 	• Take action -> observe reward and the next state
#

Q_test = test_agent(Q_table=Q, state0_A=0, state0_B=0, shares0_A=0, shares0_B=0, bal0=ACCT_BAL_0);
print('----------');
print('TESTING\n'); print(Q_test, '\n');


#
# Time how long it takes for this freaking Q-table to fill up
#

end_time = time.perf_counter();
elapsed_time = end_time - start_time;
print(f"Program executed in {elapsed_time} seconds");
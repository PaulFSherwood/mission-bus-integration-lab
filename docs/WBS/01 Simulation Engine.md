The Simulation Engine is the top-level conductor of MBIL: it does not "do" the bus logic, sensor logic, or failover logic itself, but it is responsible for creating the system, keeping track of the current tick and calling each part in the correct order every cycle so the whole simulation hehaves prdictably.

- Creating the system (What does system mean)
- keeping track of the current tick
- calling each part in the correct order every cycle

Think of it as the thing that say, 
"we are now on tick 17; 
- activate any faults scheduled for tick 17;
- let sensors publish data;
- let mission computer update;
- let the bus route messages;
- then log what happened;
- move to tick 18"
It keeps doing that until the configured run lengh is reached.

The Simulation Engine owns time, order and coordination, while the other components own behavior.

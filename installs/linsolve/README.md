The original linsolve package on github does not currently include noise while solving a linear/non-linear system of equations. We have added a subclass `LinearSolverNoise` which allow to include the noise in the system itself. If you want to use this ability, you might need to tweak the original linsolve script to the one so that it looks like the one in this folder. It is recommender to keep the original and add a  new branch with this new script and work from the current branch.
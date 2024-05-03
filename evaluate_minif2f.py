import multiprocessing as mp
import os
import utils as U
from agent import Agent
from datetime import datetime
import pytz
import logging

data_split = ["valid", "test"][0]

# setup multiprocessing logger
start_time = datetime.now(pytz.timezone(
    'America/New_York')).strftime("%Y%m%d_%H%M%S")

os.makedirs(f'logs/agent/{start_time}_logs', exist_ok=True)
logger = logging.getLogger('agent')
handler = logging.FileHandler(
    f"logs/agent/{start_time}_logs/agent.log")
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# load miniF2F problems
miniF2F_tasks = mp.Queue()
problem_names = []

completed_tasks = []
failed_tasks = []

for name in os.listdir(f"data/full_data/{data_split}"):
    path = os.path.join(f"data/full_data/{data_split}", name)
    context = U.load_json(path)
    problem_names.append((path, len(context["informal_proof"]), context))

problem_names = sorted(problem_names, key=lambda x: x[1])[2:62]
for i, (path, proof_len, _) in enumerate(problem_names):
    print(f"{i + 1}: {proof_len} chars: {path}")
print(f"Total number of problems: {len(problem_names)}\n")
    
agent = Agent(logger=logger)
corrects = 0
for i, (path, proof_len, _) in enumerate(problem_names):
    for j in range(3):
        print(f"Processing {i + 1}/{len(problem_names)}. Attempt {j+1}: {path}")
        context = U.load_json(path)
        solved = agent.attempt_formalization(context, path, i)
        if solved:
            corrects += 1
            with open(f"results/found_proofs-{start_time}.txt", "a") as f:
                f.write(f"{i}: {path} of informal length {proof_len} proved in {j+1} attempts\n")
            break
    print(f"Correct {corrects} out of {i+1}. Ratio: {corrects/(i+1)}\n")

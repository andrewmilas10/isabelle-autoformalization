import multiprocessing as mp
import os
import utils as U
from agent import BasicAgent, StepByStepAgent
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

from random import shuffle
restart_from = 0
problem_names = sorted(problem_names, key=lambda x: x[1])[restart_from:]
# shuffle(problem_names)
for i, (path, proof_len, _) in enumerate(problem_names):
    print(f"{i + 1}: {proof_len} chars: {path}")
print(f"Total number of problems: {len(problem_names)}\n")
    
# agent = BasicAgent(logger=logger)
agent = StepByStepAgent(logger=logger)
corrects = 0
for i, (path, proof_len, _) in enumerate(problem_names):
    context = U.load_json(path)
    solved, proof = agent.attempt_problem(context, path, i+restart_from)
    print("HIII", solved)
    if solved:
        corrects += 1
        with open(f"results/found_proofs-{data_split}-{start_time}.txt", "a") as f:
            f.write(f"{i+restart_from}: {path} of informal length {proof_len} proved with sol of length {len(proof)}\n")
    print(f"Correct {corrects} out of {i+restart_from+1}. Ratio: {corrects/(i+restart_from+1)}\n")

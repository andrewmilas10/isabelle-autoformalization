# isabelle-autoformalization

Code base for CPSC 428 Final Project

Code in utils directory is adapted from the repositories:
* https://github.com/albertqjiang/draft_sketch_prove/tree/main/autoformalization
* https://github.com/wiio12/LEGO-Prover/tree/master/lego_prover/utils

In order to evaluate running an agent on the miniF2F dataset:
* Add an environment variable 'OPENAI_API_KEY' with your key 
* pip install dependencies from requirements.txt 
* Install [PISA](https://github.com/albertqjiang/Portal-to-ISAbelle/tree/main) and follow README's instructions to start a PISA server
* Run 'python evaluate_minif2f.py'

from copy import copy
import os
import random
import re
import time

import utils as U
from langchain.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from lego_prover.prompts import load_prompt

from lego_prover.utils.langchain_utils import LLMMixture

checker = U.Checker(
    working_dir='/home/andrew/Isabelle2022/src/HOL/Examples',
    isa_path='/home/andrew/Isabelle2022',
    theory_file='/home/andrew/Isabelle2022/src/HOL/Examples/Interactive.thy',
    port=8172
)

class Agent:
    def __init__(
        self,
        logger=None,
        model_name="gpt-3.5-turbo",
        temperature=0,
        request_timeout=120,
    ):
        self.logger = logger
        self.logger.info("Agent initialized")
        self.llm = LLMMixture(
            model_name=model_name,
            temperature=temperature,
            request_timeout=request_timeout,
        )

        self.examples = {}
        for file in os.listdir("data/formalization_examples"):
            path = os.path.join(f"data/formalization_examples", file)
            context = U.load_json(path)
            self.examples[file[:-5]] = context["prompt"]
    
    def attempt_formalization(self, context, path, idx):
        with open("prompts/base.txt", "r") as f:
            prompt = f.read()
        for _path, prompt_text in self.examples.items():
            prompt += (prompt_text + "\n\n")
        prompt += """Informal:
        (*### Problem

        """

        p = U.LMFunction()
        prob = context["informal_statement"] + '\n\n### Solution\n\n' + context["informal_proof"] + '*)\n\nFormal:\n' + context["formal_statement"]+"\n### Isabelle Proof\n\n"
        self.logger.info("\n---------------------New Problem (%s: %s) ------------------------------------\n%s\n" % (idx+1, path, prob))
        zi = p.f(prompt, prob)
        self.logger.info("\n----------------Solution-------------------\n%s\n" % zi)
        result = checker.check(zi)
        self.logger.info("\n==== Success: %s" % result['success'])
        if result['success']:
            self.logger.info("--- Complete proof:\n%s" % result['theorem_and_proof'])
        else:
            self.logger.info("--- Reason: %s on step %s of %s" % (result['reason'], result['last_step'], result['num_steps']))
        self.logger.info("--- Complete proof:\n%s" % result['theorem_and_proof'])
        return 1 if result['success'] else 0

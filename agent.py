import os
from abc import ABC, abstractmethod
import utils as U

checker = U.Checker(
    working_dir='/home/andrew/Isabelle2022/src/HOL/Examples',
    isa_path='/home/andrew/Isabelle2022',
    theory_file='/home/andrew/Isabelle2022/src/HOL/Examples/Interactive.thy',
    port=8173
)

class Agent(ABC):
    def __init__(self, logger=None, model_name="gpt-3.5-turbo", temperature=1):
        self.logger = logger
        self.logger.info(f"{self.__class__.__name__} initialized")
        self.llm = U.LMFunction(engine=model_name, temperature=temperature)
        self.register_examples()
        self.register_base_prompts()

    @abstractmethod
    def register_examples(self):
        """Subclasses should implement this"""
        pass

    @abstractmethod
    def register_base_prompts(self):
        """Subclasses should implement this"""
        pass

    @abstractmethod
    def attempt_problem(self, examples):
        """Subclasses should implement this"""
        pass

    def check_proof(self, proof):
        result = checker.check(proof)
        self.logger.info("\n==== Success: %s" % result['success'])
        if result['success']:
            self.logger.info("--- Complete proof:\n%s" % result['theorem_and_proof'])
        # else:
        #     self.logger.info("--- Reason: %s on step %s of %s" % (result['reason'], result['last_step'], result['num_steps']))
        return result['success'], \
               result['theorem_and_proof'] if result['success'] \
                else (result['reason'], result['last_step'], result['num_steps'])

class BasicAgent(Agent):
    def __init__(self, logger=None, model_name="gpt-3.5-turbo", temperature=1):
        super().__init__(logger, model_name, temperature) 

    def register_examples(self):
        self.examples = {}
        for file in os.listdir("data/basic_agent_examples"):
            path = os.path.join(f"data/basic_agent_examples", file)
            context = U.load_json(path)
            self.examples[file[:-5]] = context["prompt"]

    def register_base_prompts(self):
        with open("prompts/basic.txt", "r") as f:
            self.base_prompt = f.read()
        for _path, prompt_text in self.examples.items():
            self.base_prompt += (prompt_text + "\n\n")
        self.base_prompt += "Informal:\n(*### Problem\n\n"
        
    def attempt_problem(self, context, path, idx):
        prob = context["informal_statement"] + '\n\n### Solution\n\n' + context["informal_proof"] + \
                '*)\n\nFormal:\n' + context["formal_statement"]+"\n### Isabelle Proof\n\n"
        self.logger.info("\n---------------------New Problem (%s: %s) ------------------------------------\n%s\n" % (idx+1, path, prob))
    
        # Attempt 3 times
        for j in range(3):
            self.logger.info(f"--------Attempt {j+1}--------\n")
            llm_proof = self.llm.f(self.base_prompt, prob)
            self.logger.info("\n----------------Solution-------------------\n%s\n" % llm_proof)
            solved, proof = self.check_proof(llm_proof)
            if solved:
                return 1, proof
        return 0, None

class StepByStepAgent(Agent):
    def __init__(self, logger=None, model_name="gpt-3.5-turbo", temperature=1):
        super().__init__(logger, model_name, temperature)
    
    def register_examples(self):
        self.decomposer_examples = {}
        for file in os.listdir("data/step_decomposer_examples"):
            path = os.path.join(f"data/step_decomposer_examples", file)
            with open(path, "r") as f:
                self.decomposer_examples[file[:-4]] = f.read()

        self.formalizer_examples = {}
        for file in os.listdir("data/step_formalizer_examples"):
            path = os.path.join(f"data/step_formalizer_examples", file)
            with open(path, "r") as f:
                self.formalizer_examples[file[:-4]] = f.read()
    
    def register_base_prompts(self):
        with open("prompts/step_decomposer.txt", "r") as f:
            self.decomposer_prompt = f.read()
        for _path, prompt_text in self.decomposer_examples.items():
            self.decomposer_prompt += (prompt_text + "\n\n")
        self.decomposer_prompt += "## Problem\n"

        with open("prompts/step_formalizer.txt", "r") as f:
            self.formalizer_prompt = f.read()
            for _path, prompt_text in self.formalizer_examples.items():
                self.formalizer_prompt += (prompt_text + "\n\n")
        self.formalizer_prompt += "Now, here is your problem. Please remember to always use sledgehammer as opposed to other proof methods such as simp or auto"+\
             " and remember to include types for expressions that involve only numbers as in the above examples. \n## Problem\n"
    
    def attempt_problem(self, context, path, idx):
        decomposer_prob = context["informal_statement"] + '\n\n## Informal proof\n' + context["informal_proof"] + \
                '\n\n## Formal statement\n' + context["formal_statement"] + "\n\n## Structured informal proof\n"
        self.logger.info("\n---------------------New Problem (%s: %s) ------------------------------------\n%s\n" % (idx+1, path, decomposer_prob))
        
        for j in range(2):
            structured_proof = self.llm.f(self.decomposer_prompt, decomposer_prob)
            self.logger.info("\n----------------Structured Proof (Attempt %d)-------------------\n%s\n" % (j+1, structured_proof))

            formalizer_prob = context["informal_statement"] + "\n\n## Structured informal proof\n" + structured_proof + \
                "\n\n## Formal statement" + context["formal_statement"] + "\n\n## Isabelle Proof\n"
            for k in range(2):
                # print(self.formalizer_prompt, formalizer_prob)
                llm_proof = self.llm.f(self.formalizer_prompt, formalizer_prob)
                self.logger.info("\n----------------Formal Proof (Attempt %d)-------------------\n%s\n" % (k+1, llm_proof))
                solved, resp = self.check_proof(llm_proof)
                if solved:
                    return 1, resp
                else: # TODO: Look into only attempting to fix the error for the proof that got the furthest
                    reason, last_step, num_steps = resp
                    solved, resp = self.try_fix_error(llm_proof, reason, last_step, num_steps)
                    if solved:
                        return 1, resp
        return 0, None
    
    def try_fix_error(self, proof, reason, last_step, num_steps, depth=0):
        env = checker._initialize()
        env.initialise()
        theory = checker.wrap_theorem(proof)
        steps = checker.get_parsed(env, theory)
        steps2 = []
        high_level_step = 0
        for i, step in enumerate(steps):
            if not (type(step) == str and "(* CHANGE " in step):
                steps2.append(step)
            if type(step) == str and "(* Step " in step:
                high_level_step += 1
            if i == last_step - 1:
                # self.logger.info(f"reason: {reason}, step: {step}, high_level_step: {high_level_step}")
                break
        last_steps = steps2[-3:]
        with open("prompts/step_fix_errors.txt", "r") as f:
            prompt = f.read()
        if "::'" in reason:
            reason += "\nNote the type of the expression in the error message suggests you might want to add specific types for step {high_level_step}\n"
        prompt += f"\n## Incorrect Proof\n{proof}\n\n## Last Statements\n{last_steps}\nIn Step {high_level_step} of the proof's comments\n\n## Reason\n{reason}\n\n## Fixed Proof\n"
        self.logger.info("\n----------------Prompt-------------------\n%s\n" % prompt)
        fixed_proof = self.llm.f(prompt, "")
        self.logger.info("\n----------------Fixed Proof-------------------\n%s\n" % fixed_proof)
        if "theorem" not in fixed_proof or "qed" not in fixed_proof or len(proof.split("theorem")) < 2:
            self.logger.info("Proof could not be fixed\n")
            return 0, None
        fixed_proof = get_theorem(fixed_proof)
        solved, resp = self.check_proof(fixed_proof)
        if solved:
            return 1, resp
        else: # TODO: Look into only attempting to fix the error for the proof that got the furthest
            if depth == 2:
                return 0, None
            reason, last_step, num_steps = resp
            return self.try_fix_error(fixed_proof, reason, last_step, num_steps, depth+1)
    
def get_theorem(proof):
    return "theorem "+proof.split("theorem")[1].split("qed")[0]+"qed"

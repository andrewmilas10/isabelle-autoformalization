# https://github.com/wellecks/ntptutorial/blob/main/partII_dsp/dsp_utils.py

import time
import os
import sys

class Checker(object):
    """A modified version of the Draft, Sketch, Prove proof-checking client.
    (https://github.com/albertqjiang/draft_sketch_prove/blob/main/autoformalization/checker.py)

    This checker supports Isabelle2022 via the new version of PISA
    (https://albertqjiang.github.io/Portal-to-ISAbelle/).

    It supports checking a miniF2F-style proof via `check`.

    Finally, it replaces `sledgehammer` with a call to `normalhammer`.
    """
    def __init__(self, working_dir, isa_path, theory_file, port=9000):
        sys.path.append(os.environ['PISA_PATH'])
        try:
            from pisa_client import initialise_env
            self.initialise_env = initialise_env
        except:
            print("Set $PISA_PATH to /yourpath/to/Portal-to-ISAbelle/src/main/python")

        self.working_dir = working_dir
        self.isa_path = isa_path
        self.theory_file = theory_file
        self.port = port

    def _initialize(self):
        env = self.initialise_env(
            self.port,
            isa_path=self.isa_path,
            theory_file_path=self.theory_file,
            working_directory=self.working_dir
        )
        return env

    def _exit(self, env):
        try:
            env.post('exit')
        except:
            print("env.post('exit') timed out")
            pass
        os.system("ps aux | grep Isabelle | awk '{print $2}' | xargs kill -9 > /dev/null 2>&1")
        os.system("ps aux | grep poly | awk '{print $2}' | xargs kill -9 > /dev/null 2>&1")

    def _parse_output(self, obs):
        """Parse the sledgehammer output, otherwise return an empty string"""
        if '<hammer>' in obs:
            output = obs.split('<hammer>')[0]
        else:
            output = ''
        return output

    def _run_step(self, step, i, tls_name, env):
        obs, reward, done, metadata = env.step_to_top_level_state(
            action=step,
            tls_name=tls_name,
            new_name='default_%d' % i
        )
        error = None
        if 'error:' in obs or 'Step error' in obs or 'Unknown error' in obs:
            error = obs
        return obs, reward, done, metadata, error

    def _run_sledgehammer(self, step, i, tls_name, env):
        # First try heuristics
        for heuristic in ['by auto', 'by simp', 'by blast', 'by fastforce', 'by force', 'by eval', 'by presburger', 'by sos', 'by arith', 'by linarith', 'by (auto simp: field_simps)']:
            step_ = step.replace('normalhammer', heuristic)
            obs, reward, done, metadata, error = self._run_step(step_, i, tls_name, env)
            if error is None:
                obs = '%s <hammer> %s' % (heuristic, obs)
                return obs, reward, done, metadata, error
        # Try sledgehammer
        out = self._run_step(step, i, tls_name, env)
        return out

    def check(self, statement_and_proof):
        # Initialize environment
        env = self._initialize()
        env.initialise()

        # Wrap and parse theorem
        theory = Checker.wrap_theorem(statement_and_proof)
        steps = Checker.get_parsed(env, theory)

        result = self._check(env, steps)
        return result

    def _check(self, env, steps):
        done = False
        reason = ''
        success = False
        step_results = []
        tls_name = 'default'
        # print(len(steps))
        for i, step in enumerate(steps):
            try:
                time0 = time.time()
                if 'simp' in step or 'auto' in step:
                    old, step = step, 'normalhammer'
                    obs, reward, done, metadata, error = self._run_sledgehammer(step, i, tls_name, env)
                    if error is not None:
                        step = old
                        obs, reward, done, metadata, error = self._run_step(step, i, tls_name, env)
                if 'normalhammer' in step:
                    obs, reward, done, metadata, error = self._run_sledgehammer(step, i, tls_name, env)
                else:
                    obs, reward, done, metadata, error = self._run_step(step, i, tls_name, env)
                step_time = time.time() - time0
                step_results.append(dict(index=i, step=step, output=self._parse_output(obs), step_time=step_time))
                # print("Andrew: Step result", step_time, obs, "rew:", reward, done, metadata, error, "\n")
                if error is not None:
                    reason = error
                    success = False
                    done = False
                    break
            except:
                # Timeout - end the proof attempt
                success = False
                done = False
                reason = 'timeout (%d)' % len(step_results)
                step_results.append(dict(index=i, step=step, output=''))
                break

            # Change when successful
            tls_name = 'default_%d' % i

        if done and reward == 1.0:
            success = True

        result = {
            'success': success,
            'reason': reason,
            'num_steps': len(steps),
            'last_step': len(step_results),
            'step_results': step_results,
            'theorem_and_proof': self.reconstruct(step_results) if success else ''
        }
        # Exit environment
        self._exit(env)
        return result
    
    @staticmethod
    def reconstruct(step_results):
        steps = []
        for step_result in step_results[1:]:
            if step_result['output'] != '':
                steps.append(step_result['output'].strip())
            else:
                steps.append(step_result['step'].strip())
        theorem_and_proof = '\n'.join(steps)
        return theorem_and_proof

    @staticmethod
    def wrap_theorem(theorem):
        return 'theory Interactive imports HOL.HOL Complex_Main "HOL-Library.Code_Target_Numeral" "HOL-Library.Sum_of_Squares" "Symmetric_Polynomials.Vieta" "HOL-Computational_Algebra.Computational_Algebra" "HOL-Number_Theory.Number_Theory" \n begin\n%s' % theorem

    @staticmethod
    def get_parsed(env, theory, tls_name='default'):
        # HACK: the parsing doesn't work well with `normalhammer`, so we replace
        # all hammer calls with sorry, then replace sorry to normalhammer after parsing.
        theory = theory.replace('sledgehammer', 'sorry')
        theory = theory.replace('normalhammer', 'sorry')

        # print("Andrew: Parsing theory", theory)
        steps = env.post(f"<parse text> ${theory}")
        steps = steps.split('<SEP>')
        # print("Andrew: Parsed steps", steps, "\n")
        steps = [s for s in steps if s.strip() != '']
        # remove weird '$' step and whitespace steps
        steps = [s for s in steps if s != '$' and s.strip() != '']
        steps = [s.replace('sorry', 'normalhammer') for s in steps]
        return steps

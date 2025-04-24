from typing import Dict, Any
from agisdk.REAL.browsergym.webclones.utils import generate_from_model
from regex import F
import jmespath
import json

class WebCloneEvaluator:
    def __init__(self, task_config: Dict[str, Any], llm: str = "gpt-4o"):
        """
        Initializes the evaluator with an optional LLM instance for fuzzy matching.
        
        Args:
            task_config: The task configuration
            llm: The model name to use
        """
        self.llm = llm
        self.task_config = task_config
    
    def jmespath_verify(self, env_state: dict, query:str):
        """
        run jmespath query evals on data, see if they return true.
        """
        try:
            jmespath_result = jmespath.search(query, env_state)
        except Exception as e:
            return False, f"Error: {e}"
        return jmespath_result, None
    
    def get_value_from_path(self, env_state: dict, path: str):
        """Helper function to retrieve a value from a nested JSON (env_state) using a dot-separated path."""
        keys = path.split(".")
        value = env_state
        error_message = None
        for key in keys:
            if not isinstance(value, dict):
                error_message = f"Error: {path} was not found in the environment state."
                return f"<env state '{path}' not found>", error_message
            value = value.get(key)
            if value is None:
                break
        return value, None

    def evaluate_with_llm(self, model_response: str, rubric: str, threshold: float = 0.8):
        """Performs fuzzy matching using an LLM."""
        fuzzy_match_prompt = f"""
            Given a student's answer and a rubric, help a teacher grade the answer. Keep in mind
            that the student may use different words or phrases to express the same idea.

            Student's answer: {model_response}
            Rubric: {rubric}

            Grade the student's answer on a scale of 0 to 1, where 1 means the student's answer matches the rubric. Don't be too strict.
            Please answer only with a floating point number and nothing else.
        """
        llm_grade = generate_from_model(prompt=fuzzy_match_prompt, model=self.llm)
        # print(f"LLM grade: {llm_grade}")
        try:
            similarity = float(llm_grade)
        except ValueError:
            similarity = 0.0
            raise ValueError("LLM response is not a valid floating point number: {llm_grade}")
        is_correct = similarity > threshold
        info = {"similarity": similarity, "model_response": model_response, "rubric": rubric}
        # print(info)
        return is_correct, info

    def jmespath_llm(self, env_state: dict, query: str, rubric: str, expected_value=True, threshold: float = 0.8):
        """
        Extract data with JMESPath and evaluate it using LLM against a rubric.
        
        Args:
            env_state: The environment state
            query: JMESPath query to extract data from the environment
            rubric: Criteria for evaluation
            expected_value: Whether this criterion SHOULD be met (True) or NOT be met (False) 
                           for the overall task to succeed
            threshold: Similarity threshold for considering correct
        """
        # Extract data from environment state using JMESPath
        jmespath_result, error = self.jmespath_verify(env_state, query)
        
        if error:
            return False, {"error": error}
        
        # Convert result to string for LLM evaluation
        result_str = str(jmespath_result)
        
        # Let the LLM evaluate if the content meets the rubric
        llm_evaluation = self.evaluate_with_llm(result_str, rubric, threshold)
        
        # Handle different return formats from evaluate_with_llm
        if isinstance(llm_evaluation, tuple):
            content_meets_criteria, eval_info = llm_evaluation
        else:
            content_meets_criteria = bool(llm_evaluation)
            eval_info = {"rubric": rubric}
        
        # The criterion is met if:
        # - expected_value is True AND content meets criteria, OR
        # - expected_value is False AND content does NOT meet criteria
        criterion_is_met = (content_meets_criteria == expected_value)
        
        # Build comprehensive info dictionary
        info = {
            "jmespath_result": jmespath_result,
            "query": query,
            "rubric": rubric,
            "content_meets_criteria": content_meets_criteria,
            "expected_to_meet_criteria": expected_value,
            "criterion_met": criterion_is_met
        }
        
        # Add any additional info from the LLM evaluation
        if isinstance(eval_info, dict):
            info.update(eval_info)
        
        return criterion_is_met, info

    def exact_match(self, actual_value: str, expected_value: str):
        """Checks if the actual value matches the expected value."""
        is_correct = actual_value == expected_value
        info = {"actual_value": actual_value, "expected_value": expected_value}
        return is_correct, info

    def evaluate(self, env_state: dict = None, model_response: str = None):
        results = []
        # pretty print the state using json.dumps
        print("Environment State:")
        print(json.dumps(env_state, indent=4))
        print("\n")
        for i, eval in enumerate(self.task_config.get_evals()):
            if eval.type == "llm_boolean":
                is_correct = self.evaluate_with_llm(model_response, eval.rubric)
                results.append(is_correct)
                eval_outcome = f"model response: {model_response}, rubric: {eval.rubric}, is_correct: {is_correct}"
            elif eval.type == "jmespath":
                actual_value, error_message = self.jmespath_verify(env_state, eval.query)
                if error_message:
                    is_correct = (False, error_message)
                    actual_value = error_message
                else:
                    is_correct = self.exact_match(actual_value, eval.expected_value)
                results.append(is_correct)
                eval_outcome = f"actual value: {actual_value} expected value: {eval.expected_value} , is_correct: {is_correct}"
            elif eval.type == "jmespath_llm":
                is_correct, info = self.jmespath_llm(env_state, eval.query, eval.rubric, eval.expected_value)
                results.append(is_correct)
                
                # Create descriptive evaluation outcome
                content_meets = info.get("content_meets_criteria", False)
                expected_meets = info.get("expected_to_meet_criteria", True)
                content_status = "MEETS" if content_meets else "DOES NOT MEET"
                expected_status = "SHOULD MEET" if expected_meets else "SHOULD NOT MEET"
                final_status = "✓ PASS" if is_correct else "✗ FAIL"
                
                eval_outcome = (
                    f"query: {eval.query}\n"
                    f"content {content_status} criteria | content {expected_status} criteria | {final_status}\n"
                    f"content: {info.get('jmespath_result', '')[:150]}..."
                )
            else:
                raise ValueError(f"Unknown evaluation type: {eval.type}")
            print(f"Criterion {i} {eval.description}: [{eval_outcome}]")


        # FIX HERE: Check the types of results and handle accordingly
        # This is the part that's causing the error
        final_results = []
        for result in results:
            if isinstance(result, tuple):
                # If it's a tuple, assume (bool, info) format
                final_results.append(result[0])
            elif isinstance(result, bool):
                # If it's just a boolean
                final_results.append(result)
            else:
                # For any other type, convert to boolean
                final_results.append(bool(result))

        is_correct = all(final_results)
        reward = self.task_config.task.points if is_correct else 0.0
        done = True  # Task is always considered done after evaluation
        message = "Task completed successfully!" if is_correct else "Task not completed successfully."
        info = {"results": results}
        return reward, done, message, info


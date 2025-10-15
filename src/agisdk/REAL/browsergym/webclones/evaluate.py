from typing import Dict, Any
from agisdk.REAL.browsergym.webclones.utils import generate_from_model
from agisdk.REAL.logging import logger as rich_logger
import jmespath
import json
import subprocess
import tempfile
import os
import sys
from pathlib import Path

class WebCloneEvaluator:
    def __init__(self, task_config: Dict[str, Any], llm: str = "gpt-4.1"):
        """
        Initializes the evaluator with an optional LLM instance for fuzzy matching.
        
        Args:
            task_config: The task configuration
            llm: The model name to use
        """
        self.llm = llm
        self.task_config = task_config
        
        # Get the directory where eval scripts are located
        # Use absolute path to be safe in Ray workers
        self.eval_scripts_dir = Path(__file__).parent.resolve() / "eval_scripts"
        
        # Verify the directory exists (helps catch deployment issues early)
        if not self.eval_scripts_dir.exists():
            rich_logger.warning(f"⚠️ Eval scripts directory not found: {self.eval_scripts_dir}")
    
    def jmespath_verify(self, env_state: dict, query:str):
        """
        run jmespath query evals on data, see if they return true.
        """
        try:
            is_valid = jmespath.search(query, env_state)
        except Exception as e:
            return False, f"Error: {e}"
        return is_valid, None
        
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
        try:
            similarity = float(llm_grade)
        except ValueError:
            similarity = 0.0
            raise ValueError(f"LLM response is not a valid floating point number: {llm_grade}")
        is_correct = similarity > threshold
        info = {"similarity": similarity, "model_response": model_response, "rubric": rubric}
        return is_correct, info

    def exact_match(self, actual_value: str, expected_value: str):
        """Checks if the actual value matches the expected value."""
        is_correct = actual_value == expected_value
        info = {"actual_value": actual_value, "expected_value": expected_value}
        return is_correct, info

    def execute_eval_script_subprocess(self, script_name: str, env_state: dict, model_response: str):
        """
        Execute a Python evaluation script as a subprocess.
        
        This method:
        1. Extracts full env_state (includes 'initialfinaldiff' and 'differences')
        2. Saves to a temporary JSON file
        3. Runs the Python script with the file path as argument
        4. Captures stdout to check for SUCCESS/FAILURE
        5. Cleans up the temporary file
        
        Args:
            script_name: Name of the Python script (e.g., "eval_dashdish_1.py")
            env_state: The environment state JSON from /finish endpoint
            model_response: The agent's final response
            
        Returns:
            Tuple of (is_correct: bool, info: dict)
        """
        script_path = self.eval_scripts_dir / script_name
        
        if not script_path.exists():
            error_msg = f"Evaluation script not found: {script_path}"
            rich_logger.error(f"❌ {error_msg}")
            return (False, {"error": error_msg})
        
        # Create temporary JSON file with the data
        temp_fd = None
        temp_path = None
        
        try:
            # Create a temporary file with a unique name
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.json',
                prefix=f'eval_{script_name.replace(".py", "")}_'
            )
            
            # Write the full env_state (includes initialfinaldiff, differences, etc.)
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(env_state, f, indent=2)
                temp_fd = None  # Prevent double-close
            
            rich_logger.info(f"📝 Executing {script_name} with data file: {os.path.basename(temp_path)}")
            
            # Execute the Python script using the same interpreter
            # This ensures compatibility and avoids environment mismatches
            result = subprocess.run(
                [sys.executable, str(script_path), temp_path],
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout per script
                cwd=None  # Use current working directory
            )
            
            # Get the output
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            rich_logger.info(f"🔧 Script output: {stdout}")
            if stderr:
                rich_logger.warning(f"⚠️ Script stderr: {stderr}")
            
            # Check if the output indicates success
            # Case-insensitive check for robustness
            is_correct = "SUCCESS" in stdout.upper()
            
            info = {
                "script": script_name,
                "output": stdout,
                "stderr": stderr if stderr else None,
                "return_code": result.returncode
            }
            
            return (is_correct, info)
            
        except subprocess.TimeoutExpired:
            error_msg = f"Script {script_name} timed out after 30 seconds"
            rich_logger.error(f"❌ {error_msg}")
            return (False, {"error": error_msg, "script": script_name})
            
        except Exception as e:
            error_msg = f"Error executing script {script_name}: {str(e)}"
            rich_logger.error(f"❌ {error_msg}")
            import traceback
            rich_logger.error(traceback.format_exc())
            return (False, {"error": error_msg, "script": script_name, "traceback": traceback.format_exc()})
            
        finally:
            # Clean up the temporary file
            # This happens even if an exception occurs
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except Exception:
                    pass  # Ignore errors on close
                    
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    rich_logger.info(f"🗑️ Cleaned up temp file: {os.path.basename(temp_path)}")
                except Exception as e:
                    rich_logger.warning(f"⚠️ Could not delete temp file {temp_path}: {e}")

    def evaluate(self, env_state: dict = None, model_response: str = None):
        results = []
        # Display environment state using Rich logging
        rich_logger.info("🌍 Environment State:")
        env_state_str = json.dumps(env_state, indent=4)
        rich_logger.print(f"[dim]{env_state_str}[/dim]")
        
        for i, eval in enumerate(self.task_config.get_evals()):
            if eval.type == "script":
                # Execute Python script as subprocess
                is_correct = self.execute_eval_script_subprocess(eval.script, env_state, model_response)
                results.append(is_correct)
                eval_outcome = f"script: {eval.script}, result: {is_correct[1].get('output', 'N/A')}"
                
            elif eval.type == "llm_boolean":
                is_correct = self.evaluate_with_llm(model_response, eval.rubric)
                results.append(is_correct)
                eval_outcome = f"llm eval, is_correct: {is_correct[0]}"
                
            elif eval.type == "jmespath":
                actual_value, error_message = self.jmespath_verify(env_state, eval.query)
                if error_message:
                    is_correct = (False, error_message)
                    actual_value = error_message
                else:
                    is_correct = self.exact_match(actual_value, eval.expected_value)
                results.append(is_correct)
                eval_outcome = f"jmespath query, is_correct: {is_correct[0]}"
            
            else:
                error_msg = f"Unknown evaluation type: {eval.type}"
                rich_logger.error(f"❌ {error_msg}")
                raise ValueError(error_msg)
            
            # Display criterion evaluation using Rich logging
            description = eval.description or f"Criterion {i}"
            if is_correct[0]:
                rich_logger.success(f"✅ {description}: {eval_outcome}")
            else:
                rich_logger.error(f"❌ {description}: {eval_outcome}")

        # Aggregate results
        is_correct = all(result[0] for result in results)
        reward = self.task_config.task.points if is_correct else 0.0
        done = True  # Task is always considered done after evaluation
        message = "Task completed successfully!" if is_correct else "Task not completed successfully."
        info = {"results": results}
        return reward, done, message, info

import json
import re
import jmespath
import os
from typing import Dict, Any, List, Optional, Union, Tuple
import openai

from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

def check_completion(action: str) -> bool:
    """
    Check if the action is send_msg_to_user or report_infeasible
    """
    return ("send_msg_to_user" in action) or ("report_infeasible" in action)


def evaluate(task_config, controller, observation):
    """
    Evaluate the agent's performance based on task configuration
    
    Args:
        task_config: The task configuration containing evaluation criteria
        controller: The browser controller instance
        observation: Dict containing action list and other observation data
        
    Returns:
        Dict with evaluation results containing success status, message, and details
    """
    # Go to the finish url to see the final state
    controller.goto(task_config['website']['url'] + '/finish')
    
    # Wait for the page to load and get a fresh observation
    eval_observation = controller.get_observation()
    
    # Extract environment state from the pre element
    env_state = extract_env_state(controller)
    
    # Find the model's response by looking for send_msg_to_user actions
    model_response = None
    if observation and "action_list" in observation:
        model_response = extract_model_response(observation["action_list"])
    
    if not env_state and task_config.get('challengeType') != 'retrieval':
        return {
            "success": False,
            "message": "Failed to extract environment state from evaluation page",
            "details": None
        }
    
    # Evaluate each criterion from the task config
    results = []
    for i, eval_criterion in enumerate(task_config.get('evals', [])):
        if eval_criterion['type'] == 'jmespath':
            is_correct, info = evaluate_jmespath(env_state, eval_criterion['query'], eval_criterion['expected_value'])
            results.append({
                "criterion": eval_criterion.get('description', f"Criterion {i+1}"),
                "success": is_correct,
                "details": info
            })
        elif eval_criterion['type'] == 'llm_boolean':
            # For LLM evaluations, we need the model's response
            if not model_response:
                results.append({
                    "criterion": eval_criterion.get('description', f"Criterion {i+1}"),
                    "success": False,
                    "details": "No model response found to evaluate"
                })
                continue
                
            is_correct, info = evaluate_with_llm(model_response, eval_criterion['rubric'])
            results.append({
                "criterion": eval_criterion.get('description', f"Criterion {i+1}"),
                "success": is_correct,
                "details": info
            })
        else:
            results.append({
                "criterion": eval_criterion.get('description', f"Criterion {i+1}"),
                "success": False,
                "details": f"Unsupported evaluation type: {eval_criterion['type']}"
            })
    
    # Check if all criteria were met
    all_passed = all(result['success'] for result in results)
    
    # Calculate reward
    reward = task_config.get('points', 0) if all_passed else 0.0
    
    # Prepare the evaluation result
    evaluation_result = {
        "success": all_passed,
        "message": "Task completed successfully!" if all_passed else "Task not completed successfully.",
        "reward": reward,
        "details": {
            "results": results,
            "model_response": model_response
        }
    }
    
    return evaluation_result


def extract_env_state(controller) -> Dict[str, Any]:
    """
    Extract the environment state from the evaluation page.
    
    Args:
        controller: The browser controller instance
        
    Returns:
        The parsed environment state as a dictionary
    """
    try:
        # Find the <pre> element containing the state
        state_text = controller.page.evaluate("""
            () => {
                const preElement = document.querySelector('pre');
                return preElement ? preElement.textContent : null;
            }
        """)
        
        if not state_text:
            print("No pre element found on evaluation page")
            return None
        
        # Parse the JSON content
        return json.loads(state_text)
    except Exception as e:
        print(f"Error extracting environment state: {e}")
        return None


def extract_model_response(actions: List[str]) -> Optional[str]:
    """
    Extract the model's response from the last send_msg_to_user action.
    
    Args:
        actions: List of action strings
        
    Returns:
        The model's response text or None if not found
    """
    # Look through actions in reverse to find the last send_msg_to_user
    for action in reversed(actions):
        if "send_msg_to_user" in action:
            # Using regex to extract the message content
            match = re.search(r"send_msg_to_user\('([^']*)'\)", action)
            if match:
                return match.group(1)
            
            # Try alternate format with double quotes
            match = re.search(r'send_msg_to_user\("([^"]*)"\)', action)
            if match:
                return match.group(1)
        elif "report_infeasible" in action:
            # Using regex to extract the message content
            match = re.search(r"report_infeasible\('([^']*)'\)", action)
            if match:
                return match.group(1)
            
            # Try alternate format with double quotes
            match = re.search(r'report_infeasible\("([^"]*)"\)', action)
            if match:
                return match.group(1)
    return None


def evaluate_jmespath(env_state: dict, query: str, expected_value: Any) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluate a JMESPath query against the environment state.
    
    Args:
        env_state: The environment state dictionary
        query: The JMESPath query to evaluate
        expected_value: The expected value to compare against
        
    Returns:
        Tuple of (is_correct, info) where info contains details about the evaluation
    """
    try:
        actual_value = jmespath.search(query, env_state)
        is_correct = actual_value == expected_value
        
        return is_correct, {
            "actual_value": actual_value,
            "expected_value": expected_value,
            "query": query
        }
    except Exception as e:
        return False, {
            "error": str(e),
            "query": query,
            "expected_value": expected_value
        }


def evaluate_with_llm(model_response: str, rubric: str, threshold: float = 0.8) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluate a model response against a rubric using an LLM for fuzzy matching.
    
    Args:
        model_response: The response from the agent to evaluate
        rubric: The evaluation rubric to compare against
        threshold: The similarity threshold for acceptance
        
    Returns:
        Tuple of (is_correct, info) where info contains details about the evaluation
    """
    try:
        fuzzy_match_prompt = f"""
            Given a student's answer and a rubric, help a teacher grade the answer. Keep in mind
            that the student may use different words or phrases to express the same idea.

            Student's answer: {model_response}
            Rubric: {rubric}

            Grade the student's answer on a scale of 0 to 1, where 1 means the student's answer matches the rubric. Don't be too strict.
            Please answer only with a floating point number and nothing else.
        """
        
        # Get API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not found. Using simple matching instead.")
            # Fallback to simple keyword matching if no API key
            return simple_keyword_evaluation(model_response, rubric)
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Generate LLM response
        llm_response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o as default model
            messages=[{"role": "user", "content": fuzzy_match_prompt}]
        )
        
        llm_grade = llm_response.choices[0].message.content.strip()
        
        try:
            similarity = float(llm_grade)
        except ValueError:
            print(f"Warning: LLM response is not a valid float: {llm_grade}")
            similarity = 0.0
            
        is_correct = similarity >= threshold
        
        return is_correct, {
            "similarity": similarity,
            "threshold": threshold,
            "model_response": model_response,
            "rubric": rubric
        }
    
    except Exception as e:
        print(f"Error in LLM evaluation: {e}")
        # Fallback to simple evaluation in case of error
        return simple_keyword_evaluation(model_response, rubric)


def simple_keyword_evaluation(model_response: str, rubric: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Simple fallback evaluation using keyword matching when LLM is not available.
    
    Args:
        model_response: The response from the agent to evaluate
        rubric: The evaluation rubric to compare against
        
    Returns:
        Tuple of (is_correct, info) where info contains details about the evaluation
    """
    # Extract key terms from the rubric
    # This is a very simple approach that looks for quoted terms or terms after words like "was" or "is"
    quoted_terms = re.findall(r"'([^']*)'|\"([^\"]*)\"", rubric)
    flat_quoted = [term[0] or term[1] for term in quoted_terms if term[0] or term[1]]
    
    # Look for terms after common linking verbs
    after_verb_terms = re.findall(r"\b(?:is|was|were|are)\s+'?\"?([^'\",.?!]+)", rubric)
    
    # Combine all extracted terms
    key_terms = flat_quoted + after_verb_terms
    
    # If no key terms found, use words longer than 5 characters
    if not key_terms:
        key_terms = [word for word in re.findall(r'\b\w+\b', rubric) if len(word) > 5]
    
    # Check if any key term appears in the response
    matches = [term for term in key_terms if term.lower() in model_response.lower()]
    similarity = len(matches) / len(key_terms) if key_terms else 0
    
    return similarity >= 0.5, {
        "similarity": similarity,
        "method": "simple_keyword_matching",
        "matches": matches,
        "key_terms": key_terms,
        "model_response": model_response,
        "rubric": rubric
    }


def check_action_list_completion(actions: List[str]) -> bool:
    """
    Check if the list of actions includes a completion action.
    
    Args:
        actions: List of action strings
        
    Returns:
        True if a completion action was found, False otherwise
    """
    return any(check_completion(action) for action in actions)


if __name__ == "__main__":
    import sys
    import json
    from demoagent.browsergym_sync import BrowserController
    
    if len(sys.argv) > 1:
        task_config_path = sys.argv[1]
    else:
        task_config_path = "./udriver-2.json"
    
    # Load the task configuration
    with open(task_config_path, 'r') as f:
        task_config = json.load(f)
    
    # Initialize the browser controller
    with BrowserController() as controller:
        # Navigate to the website
        print(f"Navigating to {task_config['website']['url']}...")
        controller.goto(task_config['website']['url'])
        
        # Demo mode - allow manual actions
        print("\nEnter BrowserGym actions to complete the task")
        print("Press Enter with no input to evaluate the current state")
        print("Enter 'q' to quit")
        
        actions = []
        while True:
            action = input("> ")
            if action.lower() in ['q', 'quit', 'exit']:
                break
            elif action.strip() == '':
                # Empty input - evaluate current state
                observation = {"actions": actions}
                result = evaluate(task_config, controller, observation)
                print("\nEvaluation Result:")
                print(json.dumps(result, indent=2))
                print("\nCriteria Details:")
                for i, criterion in enumerate(result.get("details", {}).get("results", [])):
                    success = "✓" if criterion["success"] else "✗"
                    print(f"{i+1}. {success} {criterion['criterion']}")
                print(f"\nOverall Result: {'PASSED' if result['success'] else 'FAILED'}")
                break
            else:
                # Execute the action
                result = controller.execute_action(action)
                if result["success"]:
                    actions.append(action)
                    print(f"Action executed successfully")
                else:
                    print(f"Action failed: {result['error']}")
                
                # Get updated observation
                observation = controller.get_observation()
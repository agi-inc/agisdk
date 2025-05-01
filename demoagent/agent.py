import json
import os
import time
import logging
from rich import print
from browsergym_sync import BrowserController
from agent_utils import get_agent_action
from evaluation_utils import evaluate, check_completion

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def run_agent(model_config, task_config, experiment_config, return_training_data=False, verbose=False):
    
    # Record data if return_training_data is True
    if return_training_data:
        training_data = {
            'task_config': task_config,
            'experiment_config': experiment_config,
            'model_config': model_config,
            'training_data': []
        }
    
    if verbose:
        print(f"Running agent for task {task_config['id']} with run_id {experiment_config['run_id']}")
    
    # Agent loop 
    with BrowserController() as controller:
        controller.set_show_generic_nodes(experiment_config['show_generic'])
        
        url = task_config['website']['url']
        config_url = url + f"/config?run_id={experiment_config['run_id']}&task_id={experiment_config['task_id']}&latency=0"
        
        controller.goto(config_url)
        controller.page.wait_for_load_state("networkidle")
        
        controller.goto(url)
        controller.page.wait_for_load_state("networkidle")
                    
        # Build observation
        observation = {
            'axtree': controller.format_axtree(controller.get_observation()),
            'action_list': [],
            'previous_action_error': None,
            'step_number': 0,
        }
        
        if verbose:
            print(f"Observation: {observation}")
        
        # Agent loop
        while True:
            if observation['step_number'] >= experiment_config['max_steps']:
                break
            
            observation['step_number'] += 1
            
            # Get action
            action, prompt, response = get_agent_action(observation, model_config, task_config)
            
            if return_training_data:
                training_data['training_data'].append({
                    'prompt': prompt,
                    'response': response,
                    'action': action,
                    'step_number': observation['step_number'],
                })
            
            if verbose:
                print(f"Action: {action}")
                
            # Log action to Multion API if logger is available
            if "logger" in model_config and model_config["logger"] is not None:
                try:
                    model_config["logger"].log_step(
                        {"step": observation['step_number'], "action_input": prompt[:1000] + "..." if len(prompt) > 1000 else prompt},
                        {"action": action}
                    )
                except Exception as e:
                    logging.warning(f"Failed to log action to Multion API: {e}")
            
            # Execute action
            result = controller.execute_action(action)
            result_error = result['error']
            time.sleep(3)
            
            # Update observation
            observation['axtree'] = controller.format_axtree(controller.get_observation())
            observation['action_list'].append(action)
            observation['previous_action_error'] = result_error
            
            if verbose:
                print(f"Observation: {observation}")
            
            # check if action is loop ending
            if check_completion(action):
                break
            
        # Evaluate the agent
        evaluation = evaluate(task_config, controller, observation)
        evaluation['task_id'] = task_config['id']
        print(f"Task {task_config['id']} Success: {evaluation['success']}")
        
        if return_training_data:
            for data in training_data['training_data']:
                data['reward'] = 1 if evaluation['success'] else 0
        
        if return_training_data:
            training_data['evaluation'] = evaluation
            return training_data
        else:
            return evaluation

if __name__ == "__main__":
    from agisdk.REAL.tasks import all_tasks as tasks
    
    # Log the system prompt
    # with open(os.path.join(os.path.dirname(__file__), "SYSTEM_PROMPT.md"), "r") as f:
    #     system_prompt = f.read()
    #     #logging.info(f"System Prompt:\n{system_prompt}")
    
    # Log the actions documentation
    with open(os.path.join(os.path.dirname(__file__), "ACTIONS.md"), "r") as f:
        actions_doc = f.read()
        logging.info(f"Available Actions:\n{actions_doc}")
        
    # Initialize the Multion logger
    from agent_logger_class import AgentLogger
    # Use environment variable for API key
    agent_logger = AgentLogger("Agent execution starting", api_key=os.environ.get("MULTION_API_KEY", ""))
    
    logging.info("Agent execution starting...")
    
    with open('/Users/pran-ker/Developer/agisdk/demoagent/udriver-1.json', 'r') as f:
        task_config = json.load(f)
        logging.info(f"Task config loaded: {task_config['id']}")
    
    # OpenAI model
    model_config = {
        "model_provider": "openai",
        "model_name": "gpt-4o-mini",
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "response_kwargs": {},
        "logger": agent_logger  # Add the Multion API logger
    }
    
    logging.info(f"Using model: {model_config['model_provider']} - {model_config['model_name']}")
    
    # Run experiment
    experiment_config = {
        "max_steps": 4,
        "show_generic": False,
        "run_id": "0",
        "task_id": "1"
    }
    
    evaluation = run_agent(model_config, task_config, experiment_config, return_training_data=True, verbose=True)
    print(evaluation)
    
    logging.info("Agent execution completed.")
    logging.info(f"Task {task_config['id']} Success: {evaluation['evaluation']['success']}")
    
    # Log the final results to Multion API
    try:
        # Create a simplified version of evaluation data
        eval_data = {
            "success": evaluation['evaluation']['success'],
            "message": evaluation['evaluation']['message'],
            "reward": evaluation['evaluation']['reward']
        }
        
        # Include action history in the final log
        action_history = []
        if 'training_data' in evaluation:
            action_history = [item.get('action', '') for item in evaluation['training_data']]
        
        agent_logger.log_step(
            {"task_id": task_config['id'], "status": "completed"},
            {
                "evaluation": eval_data,
                "action_history": action_history if action_history else []
            }
        )
        
        # Finalize the logging session
        agent_logger.complete()
    except Exception as e:
        logging.error(f"Error logging results to Multion API: {e}")
    
    # Log the final results
    logging.info(f"Full evaluation results: {json.dumps(evaluation['evaluation'], indent=2)}")
    logging.info(f"Prompt/response logs saved to agent_prompts.log")
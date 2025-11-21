# REAL Evals Task Creation Guide

Follow 3 steps to create tasks for REAL:

1. Try task yourself
2. Define evaluator for task
3. Repeat task and verify evaluator works\!

# 1\. Try task yourself

* Go to any of the sites from [real evals](http://realevals.xyz) in a new private chromium browser window
* Invent a task and do it. For example, on the amazon clone, buy a water bottle and check out
* Go to `<BASE_SITE_URL>/finish`. For example, `http://evals-omnizon.vercel.app/finish`
* Events tracked by the website are shown here in `JSON`. For example, if you bought a water bottle, it would display within the rendered `JSON` object. State check evals will be run against this.
* Copy the text on this page.

# 2\. Define evaluator for task

Let’s look at an evaluator in the REAL leaderboard to get an idea for how to write them.

`task.json`

```json
{
  "id": "zilloft-9",
  "goal": "Find the most expensive home listed in San Francisco with 4+ bedrooms and request a tour for 6:00 PM on the earliest possible date. Use these contact details: Name: David Smith, Email: davidsmith@example.com, Phone: 555-333-7890. What is the price of this home?",
  "website": {
    "id": "zilloft",
    "name": "Zilloft",
    "similarTo": "Zillow",
    "previewImage": "/websitePreviews/zilloft_preview.jpg",
    "url": "https://real-topwork-di5dy23op-real-sites.vercel.app/"
  },
  "difficulty": "hard",
  "challengeType": "retrieval-action",
  "possible": true,
  "evals": [
    {
      "description": "tour request submitted",
      "type": "jmespath",
      "expected_value": true,
      "query": "differences.requestTours.added != null && length(differences.requestTours.added) > `0`"
    },
    {
      "description": "correct name provided",
      "type": "jmespath",
      "expected_value": "David Smith",
      "query": "differences.requestTours.added.\"0\".requestTourData.formValues.name"
    },
    {
      "description": "correct email provided",
      "type": "jmespath",
      "expected_value": "davidsmith@example.com",
      "query": "differences.requestTours.added.\"0\".requestTourData.formValues.email"
    },
    {
      "description": "correct phone provided",
      "type": "jmespath",
      "expected_value": "555-333-7890",
      "query": "differences.requestTours.added.\"0\".requestTourData.formValues.phone"
    },
    {
      "description": "correct time selected",
      "type": "jmespath",
      "expected_value": "6:00 PM",
      "query": "differences.requestTours.added.\"0\".requestTourData.options[0].time"
    },
    {
      "description": "found correct price",
      "type": "llm_boolean",
      "expected_value": true,
      "rubric": "Does the answer correctly state that the price of the most expensive home in San Francisco with 4+ bedrooms is $4,985,000?"
    }
  ],
  "points": 1,
  "config": {}
}
```


As you can see, there are the task is defined by a few key things:

* ID: a unique id for the task
* Website: which site the task should be performed on
* Goal: a prompt for what the agent needs to do
* Evals: the tests to check if the agent was successful. For the agent to succeed, it must pass all evals.

There are two different types of evals:

* `llm_boolean`: A check on the final response of the agent, powered by an LLM
* `jmespath`: a check written on the final internal state of the site (shown on the `/finish` url), written in the `JSON` query language `jmespath`. It returns a value and if the returned value is equivalent to `expected_value`, the check passes

Writing these `jmespath` queries can be a bit cumbersome. So, I made a website to help create them:

[https://eval-genie-checks-maker.lovable.app/](https://eval-genie-checks-maker.lovable.app/)

Just paste in your final state from the `/finish` url and write down the initial task goal, and the website will generate candidate `jmespath` queries \+ run them and show their results in the UI. Select which ones you want of the candidates, then click the copy selected button to copy the evals (already in the correct format) and paste them into your task definition.

Now save your task as a json file in your working directory.

# 3\. Repeat Task and verify evaluator works

Now that you have your task in a json format, it is good practice to solve it as a human and actually verify that the evaluator passes you as correct.

To do this

`pip install agisdk nova-act`

Create a folder named `tasks` in your working directory, and put your json task file in it.

 run this code:

```python
import argparse
import json
import os
import glob
from nova_act import NovaAct
from agisdk.REAL.browsergym.webclones.evaluate import WebCloneEvaluator
from agisdk.REAL.browsergym.webclones.task_config import TaskConfig
from datetime import datetime

# Task loading functions
def load_local_tasks(task_filter=None):
    local_tasks = []
    task_files = glob.glob(os.path.join(os.path.dirname(__file__), "tasks/*.json"))

    print(f"Found {len(task_files)} task files")

    for task_file in task_files:
        with open(task_file, 'r') as f:
            task = json.load(f)
            if task_filter is None or task_filter == "" or task["id"] == task_filter:
                local_tasks.append(task)

    return local_tasks

# NovaAct execution
def run_task(task: dict, run_id: str, headless: bool = True) -> dict:
    tid, goal, base = task["id"], task["goal"], task["website"]["url"]
    cfg = f"{base}/config?run_id={run_id}&task_id={tid}"

    result = {
        "id": tid,
        "task_id": tid,
        "start_time": datetime.now().isoformat(),
        "ok": False,
        "success": False,
        "error": None,
        "response": None,
        "elapsed_time": 0,
        "t": 0
    }

    print(f"Starting task: {tid} - {goal[:200]}...")
    try:
        with NovaAct(starting_page=cfg, headless=headless) as bot:
            bot.go_to_url(base)
            try:
                result["response"] = input("Press Enter when ready to finish:")

                # Finish the task
                bot.go_to_url(f"{base}/finish")

                pre_element = bot.page.wait_for_selector("pre")
                if pre_element:
                    env_state = json.loads(pre_element.inner_text())

                # import code; code.interact(local=locals())

                config_path = os.path.join(os.path.dirname(__file__), f"v1/tasks/{tid}.json")
                config_json = TaskConfig(config_path, is_path=True)
                evaluator = WebCloneEvaluator(task_config=config_json)
                reward, done, message, info = evaluator.evaluate(env_state=env_state, model_response=result["response"])
                print(f"Evaluation result: {message}, Reward: {reward}")

                result["ok"] = True
                result["success"] = done
            except Exception as e:
                print(f"Error during act: {e}")
                result["error"] = str(e)
    except Exception as e:
        print(f"Error setting up NovaAct: {e}")
        result["error"] = str(e)

    return result


def main():
    p = argparse.ArgumentParser("NovaAct Local Tasks")
    p.add_argument("--filter", default="", help="Task ID filter (empty for all tasks)")
    p.add_argument("--run-id", default="b0c2f93d0c461eed5b99b51ed6e934baa600ba0907185edd93c949ab20f34d21")
    p.add_argument("--no-headless", action="store_false")
    args = p.parse_args()

    # Load tasks from local directory
    tasks = load_local_tasks(args.filter)
    print(f"Running {len(tasks)} tasks")

    # Run each task
    results = []
    for task in tasks:
        result = run_task(task, args.run_id, not args.no_headless)
        results.append(result)

    return results




if __name__ == "__main__":
    main()
    '''


### **Congrats 🎉**

You just invented, created, and tested your first task on REAL\!

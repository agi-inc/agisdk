#!/usr/bin/env python3
import json
import os
from pathlib import Path
import csv

def process_summary_files(results_dir):
    results = []
    
    # Find all summary_info.json files
    for root, dirs, files in os.walk(results_dir):
        if 'summary_info.json' in files:
            json_path = os.path.join(root, 'summary_info.json')
            
            try:
                with open(json_path, 'r') as f:
                    data = json.load(f)
                
                # Process all files (no model_name filter)
                if True:  # Process all summary files
                    # Extract required fields
                    task_id = data.get('task_id', '')
                    # Remove the prefix and suffix from task_id to match opus format
                    if task_id.startswith('webclones.'):
                        task_id = task_id[10:]  # Remove 'webclones.' prefix
                    if '_' in task_id:
                        task_id = task_id.rsplit('_', 1)[0]  # Remove the numeric suffix
                    
                    run_id = "465bba48-5ee9-4df8-aacf-1f24b574b8e2"  # Set to requested run_id
                    cum_reward = data.get('cum_reward', 0)
                    
                    # Apply cum_reward > 0 condition
                    if cum_reward > 0:
                        evals_passed = '["eval1"]'
                        evals_failed = '[]'
                    else:
                        evals_passed = '[]'
                        evals_failed = '["eval1"]'
                    
                    results.append({
                        'task_id': task_id,
                        'run_id': run_id,
                        'evals_passed': evals_passed,
                        'evals_failed': evals_failed,
                        'cum_reward': cum_reward
                    })
                    
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error processing {json_path}: {e}")
                continue
    
    return results

def main():
    results_dir = "/Users/pran-ker/Developer/agisdk/results"
    
    if not os.path.exists(results_dir):
        print(f"Results directory not found: {results_dir}")
        return
    
    print("Processing summary files...")
    results = process_summary_files(results_dir)
    
    print(f"\nFound {len(results)} summary files processed")
    print("="*80)
    
    # Display results
    for i, result in enumerate(results, 1):
        print(f"{i:3d}. task_id: {result['task_id']}")
        print(f"     run_id: {result['run_id']}")
        print(f"     evals_passed: {result['evals_passed']}")
        print(f"     evals_failed: {result['evals_failed']}")
        print(f"     cum_reward: {result['cum_reward']}")
        print()
    
    # Save to CSV for easy processing
    csv_path = "/Users/pran-ker/Developer/agisdk/combined_results.csv"
    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = ['task_id', 'run_id', 'evals_passed', 'evals_failed']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            # Only write the required fields, excluding cum_reward
            row = {
                'task_id': result['task_id'],
                'run_id': result['run_id'],
                'evals_passed': result['evals_passed'],
                'evals_failed': result['evals_failed']
            }
            writer.writerow(row)
    
    print(f"Results saved to: {csv_path}")
    
    # Summary statistics
    passed_count = sum(1 for r in results if r['cum_reward'] > 0)
    failed_count = len(results) - passed_count
    
    print(f"\nSummary:")
    print(f"Total experiments: {len(results)}")
    print(f"Passed (cum_reward > 0): {passed_count}")
    print(f"Failed (cum_reward <= 0): {failed_count}")
    print(f"Success rate: {passed_count/len(results)*100:.1f}%" if results else "N/A")

if __name__ == "__main__":
    main()
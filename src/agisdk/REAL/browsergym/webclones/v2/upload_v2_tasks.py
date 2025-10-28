#!/usr/bin/env python3
"""
Script to fetch tasks table structure and upload all v2 tasks to Supabase.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = "https://mnwlhrlwrguhtfidnjts.supabase.co"
# Using service role key for full access
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1ud2xocmx3cmd1aHRmaWRuanRzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMjMwNTE4MCwiZXhwIjoyMDQ3ODgxMTgwfQ.QxQHo2qHNzONLs1Z4aTzv33mz98cQzI9TfWQvsaJclM"

def fetch_table_structure(supabase: Client) -> None:
    """Fetch and display the structure of the tasks table."""
    try:
        # Fetch a sample row to understand the structure
        result = supabase.table("tasks").select("*").limit(1).execute()

        if result.data and len(result.data) > 0:
            sample = result.data[0]
            print("\n--- Tasks Table Structure ---")
            print("Columns found in tasks table:")
            for key, value in sample.items():
                value_type = type(value).__name__
                print(f"  - {key}: {value_type} (sample: {str(value)[:50]}...)")
        else:
            print("No existing data in tasks table to analyze structure")

    except Exception as e:
        print(f"Error fetching table structure: {e}")
        print("Table might be empty or doesn't exist yet")

def load_v2_tasks(tasks_dir: Path) -> List[Dict[str, Any]]:
    """Load all JSON task files from the v2 tasks directory."""
    tasks = []

    # Get all JSON files in the tasks directory
    json_files = sorted(tasks_dir.glob("*.json"))

    print(f"\nFound {len(json_files)} v2 task files in {tasks_dir}")

    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                task_data = json.load(f)
                # Ensure the task is marked as v2
                task_data['version'] = 'v2'
                tasks.append(task_data)
                print(f"  ✓ Loaded: {task_data.get('id', 'unknown')}")
        except Exception as e:
            print(f"  ✗ Error loading {json_file.name}: {e}")

    return tasks

def upload_v2_tasks(tasks: List[Dict[str, Any]], supabase: Client) -> None:
    """Upload v2 tasks to Supabase tasks table."""
    print(f"\n--- Uploading {len(tasks)} v2 Tasks ---")

    success_count = 0
    error_count = 0

    for task in tasks:
        try:
            # Prepare record matching the actual table structure
            task_record = {
                "task_id": "v2." + task.get("id"),  # Format: v2.dashdish-1
                "website_id": task.get("website", {}).get("id", ""),  # Extract website id
                "goal": task.get("goal"),
                "difficulty": task.get("difficulty"),
                "challenge_type": task.get("challengeType"),  # Map challengeType to challenge_type
                "evals": task  # Store the entire task data in evals field
            }

            # Use insert (not upsert since 'id' is auto-generated)
            response = supabase.table("tasks").insert(
                task_record
            ).execute()

            success_count += 1
            print(f"  ✓ Uploaded: {task.get('id')}")

        except Exception as e:
            error_count += 1
            print(f"  ✗ Failed: {task.get('id', 'unknown')} - Error: {e}")

    print(f"\n--- Upload Summary ---")
    print(f"✓ Successfully uploaded: {success_count} tasks")
    if error_count > 0:
        print(f"✗ Failed uploads: {error_count} tasks")
    print(f"📊 Total processed: {len(tasks)} v2 tasks")

def verify_upload(supabase: Client) -> None:
    """Verify that v2 tasks were uploaded successfully."""
    try:
        # Count v2 tasks in the database (using task_id pattern)
        result = supabase.table("tasks").select("task_id, goal").like("task_id", "v2.%").execute()
        v2_tasks = result.data if result.data else []
        v2_count = len(v2_tasks)

        print(f"\n--- Verification ---")
        print(f"Total v2 tasks in database: {v2_count}")

        # Show a few examples
        if v2_count > 0:
            print("\nSample v2 tasks in database:")
            for task in v2_tasks[:5]:
                goal_preview = task['goal'][:60] + "..." if len(task['goal']) > 60 else task['goal']
                print(f"  - {task['task_id']}: {goal_preview}")

    except Exception as e:
        print(f"Error during verification: {e}")

def main():
    """Main function to execute the upload process."""

    # Get the tasks directory
    tasks_dir = Path(__file__).parent / "tasks"

    if not tasks_dir.exists():
        print(f"Error: Tasks directory not found at {tasks_dir}")
        return

    # Initialize Supabase client
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"✓ Connected to Supabase")
    except Exception as e:
        print(f"✗ Error connecting to Supabase: {e}")
        return

    # Fetch current table structure
    fetch_table_structure(supabase)

    # Load all v2 tasks
    tasks = load_v2_tasks(tasks_dir)

    if not tasks:
        print("No v2 tasks found to upload")
        return

    # Upload v2 tasks
    upload_v2_tasks(tasks, supabase)

    # Verify upload
    verify_upload(supabase)

if __name__ == "__main__":
    main()
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
SUPABASE_URL = "https://mnwlhrlwrguhtfidjnts.supabase.co"
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
            # The task data already matches the expected structure
            # Just upload it as-is since it contains all the fields
            task_record = {
                "id": "v2." + task.get("id"),  # Use task ID directly
                "goal": task.get("goal"),
                "website": task.get("website"),  # Keep as object/dict
                "difficulty": task.get("difficulty"),
                "challengeType": task.get("challengeType"),  # Keep camelCase as in source
                "possible": task.get("possible"),
                "evals": task.get("evals"),  # Keep as array
                "points": task.get("points"),
                "config": task.get("config"),  # Keep as object
                "version": "v2"  # Ensure it's marked as v2
            }

            # Use upsert to update if exists or insert if new
            response = supabase.table("tasks").upsert(
                task_record,
                on_conflict="id"  # Use id as the unique identifier
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
        # Count v2 tasks in the database
        result = supabase.table("tasks").select("id").eq("version", "v2").execute()
        v2_count = len(result.data) if result.data else 0

        print(f"\n--- Verification ---")
        print(f"Total v2 tasks in database: {v2_count}")

        # Show a few examples
        if v2_count > 0:
            examples = supabase.table("tasks").select("id, goal").eq("version", "v2").limit(3).execute()
            if examples.data:
                print("\nSample v2 tasks in database:")
                for task in examples.data:
                    print(f"  - {task['id']}: {task['goal'][:60]}...")

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
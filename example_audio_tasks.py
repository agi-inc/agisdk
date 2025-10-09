#!/usr/bin/env python3
"""
Example script showing how to use audio tasks with the AGI SDK.
"""

from agisdk import REAL
import os
import json

def list_audio_tasks():
    """List all available audio tasks."""
    from agisdk.REAL.browsergym.webclones.task_config import AUDIO_TASKS

    print(f"\n📊 Found {len(AUDIO_TASKS)} audio tasks")
    print("\nSample audio tasks:")
    for task in AUDIO_TASKS[:10]:  # Show first 10
        print(f"  - {task}")

    return AUDIO_TASKS

def show_audio_task_details(task_id="dashdish-1"):
    """Show details of a specific audio task."""
    from agisdk.REAL.browsergym.webclones.task_config import TaskConfig

    print(f"\n🎯 Loading audio task: {task_id}")

    # Load task configuration
    config = TaskConfig(task_id, use_audio=True)
    task_data = config.config_json

    print(f"\nTask Details:")
    print(f"  ID: {task_data.get('id', 'N/A')}")
    print(f"  Goal: {task_data.get('goal', 'N/A')}")
    print(f"  Difficulty: {task_data.get('difficulty', 'N/A')}")
    print(f"  Challenge Type: {task_data.get('challengeType', 'N/A')}")

    if 'audio_files' in task_data:
        print(f"\n🎵 Audio files available:")
        for lang, path in task_data['audio_files'].items():
            exists = "✅" if os.path.exists(path) else "❌"
            print(f"    {lang}: {exists} {os.path.basename(path)}")

    return task_data

def run_audio_task_with_harness(task_id="dashdish-1", model="gpt-4o"):
    """Run an audio task using the REAL harness."""
    print(f"\n🚀 Running audio task: {task_id} with model: {model}")

    # Create harness with audio task
    # Note: Audio tasks are registered with "audio." prefix
    harness = REAL.harness(
        model=model,
        task_name=f"audio.{task_id}",  # Use audio prefix
        headless=True,  # Set to False to watch the browser
        max_steps=25
    )

    # Run the task
    print("\n🎮 Executing task...")
    result = harness.run()

    # Display results
    print(f"\n📊 Results:")
    print(f"  Success: {result.get('success', 'N/A')}")
    print(f"  Reward: {result.get('cum_reward', 0)}")
    print(f"  Steps taken: {result.get('n_steps', 0)}")

    return result

def process_audio_instruction(task_id="dashdish-1", language="english"):
    """
    Process audio instruction for a task.
    Note: This is a placeholder - actual audio processing would require
    a speech-to-text library like whisper or Google Speech API.
    """
    from agisdk.REAL.browsergym.webclones.task_config import TaskConfig

    print(f"\n🎤 Processing audio for task: {task_id} in {language}")

    # Load task with audio
    config = TaskConfig(task_id, use_audio=True)
    task_data = config.config_json

    if 'audio_files' in task_data and language in task_data['audio_files']:
        audio_path = task_data['audio_files'][language]
        print(f"  Audio file: {audio_path}")
        print(f"  File exists: {os.path.exists(audio_path)}")

        # Here you would typically process the audio file
        # For example, using OpenAI Whisper:
        # import whisper
        # model = whisper.load_model("base")
        # result = model.transcribe(audio_path)
        # transcription = result["text"]

        print(f"\n  💡 To process audio, install a speech-to-text library:")
        print(f"     pip install openai-whisper")
        print(f"     Then use: whisper.transcribe(audio_path)")

        return audio_path
    else:
        print(f"  ❌ No audio file found for language: {language}")
        return None

def main():
    """Main function to demonstrate audio task usage."""
    print("=" * 60)
    print("🎵 AGI SDK Audio Tasks Demo")
    print("=" * 60)

    # 1. List available audio tasks
    audio_tasks = list_audio_tasks()

    # 2. Show details of a specific audio task
    if audio_tasks:
        task_details = show_audio_task_details(audio_tasks[0])

    # 3. Process audio instruction (placeholder)
    audio_path = process_audio_instruction(audio_tasks[0] if audio_tasks else "dashdish-1")

    # 4. Run an audio task (requires API key)
    print("\n" + "=" * 60)
    print("💡 To run audio tasks with an AI model:")
    print("   1. Set your API key: export OPENAI_API_KEY='your-key'")
    print("   2. Uncomment the line below and run again")
    print("=" * 60)

    # Uncomment to actually run a task:
    # if os.environ.get("OPENAI_API_KEY"):
    #     result = run_audio_task_with_harness(audio_tasks[0], "gpt-4o")
    # else:
    #     print("\n⚠️  No API key found. Set OPENAI_API_KEY to run tasks.")

if __name__ == "__main__":
    main()
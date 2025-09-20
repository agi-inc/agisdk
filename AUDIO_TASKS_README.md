# Audio Tasks for AGI SDK

This extends the AGI SDK to support multilingual audio tasks for web automation testing.

## What's New

- **112 audio tasks** with the same structure as regular tasks
- **5 language versions** per task: English, French, German, Hindi, Japanese
- **Seamless integration** with existing AGI SDK harness

## Quick Setup

1. Copy the `audio_tasks` folder to:
   ```
   src/agisdk/REAL/browsergym/webclones/audio_tasks/
   ```

2. The system automatically detects and registers audio tasks with `audio.` prefix

## Usage

### Run Audio Tasks

```python
from agisdk import REAL

# Run an audio task (same as regular tasks, just use audio. prefix)
harness = REAL.harness(
    model="gpt-4o",
    task_name="audio.dashdish-1",  # Note: audio. prefix
    headless=False
)

result = harness.run()
```

### Access Audio Files

```python
from agisdk.REAL.browsergym.webclones.task_config import TaskConfig

# Load task with audio
config = TaskConfig("dashdish-1", use_audio=True)
task_data = config.config_json

# Audio files are in the config
if 'audio_files' in task_data:
    print(task_data['audio_files'])
    # {'english': 'path/to/english.mp3', 'french': 'path/to/french.mp3', ...}
```

### Process Audio (Example with Whisper)

```python
# Install: pip install openai-whisper
import whisper

# Load task
config = TaskConfig("dashdish-1", use_audio=True)
audio_path = config.config_json['audio_files']['english']

# Transcribe
model = whisper.load_model("base")
result = model.transcribe(audio_path)
print(result["text"])  # The transcribed instruction
```

## Task Structure

```
audio_tasks/
├── dashdish/        # 11 tasks
├── fly-unified/     # 14 tasks
├── gocalendar/      # 10 tasks
├── gomail/          # 8 tasks
├── networkin/       # 10 tasks
├── omnizon/         # 10 tasks
├── opendining/      # 10 tasks
├── staynb/          # 9 tasks
├── topwork/         # 9 tasks
├── udriver/         # 11 tasks
└── zilloft/         # 10 tasks
```

Each task folder contains:
- `task.json` - Same format as regular tasks
- `english.mp3`, `french.mp3`, `german.mp3`, `hindi.mp3`, `japanese.mp3`

## Integration Details

The audio tasks:
- Use the **same evaluation system** as regular tasks
- Work with the **same harness** and agents
- Have the **same difficulty levels** and challenge types
- Just add **audio files** as an additional input option

## Example: Run All Audio Tasks

```python
from agisdk import REAL
from agisdk.REAL.browsergym.webclones.task_config import AUDIO_TASKS

# Run all audio tasks
for task_id in AUDIO_TASKS[:5]:  # Run first 5
    harness = REAL.harness(
        model="gpt-4o",
        task_name=f"audio.{task_id}",
        headless=True
    )
    result = harness.run()
    print(f"{task_id}: {result['success']}")
```

## Statistics

- **Total**: 112 tasks
- **Difficulty**: Easy (29), Medium (56), Hard (27)
- **Types**: Action (56), Retrieval (27), Retrieval-Action (27), No-Action (2)
- **Languages**: 5 per task = 560 total audio files

## Notes

- Audio tasks are registered with `audio.` prefix to distinguish from regular tasks
- The task trajectory and evaluation remain identical to regular tasks
- Audio processing (speech-to-text) is not included - use your preferred library
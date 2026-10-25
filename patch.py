import re
with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''### Basic Execution:
To run the full pipeline on a video (skipping visual analytics since diarization is absent):
`ash
python cli.py --input data/input/sample.mp4
`

### Full Execution with Visual Analytics:
Visual processing currently requires a pre-computed diarization JSON (to isolate the candidate's speech). Pass it via --diarization:
`ash
python cli.py --input data/input/sample.mp4 --diarization data/diarization/segments.json
`'''

replacement = '''### Diarization & Role Assignment
The pipeline automatically identifies Candidate vs. Interviewer speech.
- **Automatic Mode**: Automatically triggered if --diarization is omitted. The pipeline extracts full audio, runs Silero VAD, extracts speaker embeddings via WeSpeaker, clusters them via scikit-learn, and assigns the Candidate role to the speaker with the longest duration.
  *LIMITATION*: The duration heuristic assumes a typical interview where the candidate dominates talk time. It may mislabel speakers in highly conversational scenarios.
- **Precomputed Mode**: If you provide an existing JSON via --diarization, it skips automatic extraction and uses the provided segments.

### Basic Execution (Automatic Diarization & Visuals):
To run the full pipeline, automatically generating diarization and visual analytics:
`ash
python cli.py --input data/input/sample.mp4
`

### Precomputed Diarization:
To bypass automatic diarization and use an existing JSON:
`ash
python cli.py --input data/input/sample.mp4 --diarization data/diarization/segments.json
`'''

new_content = content.replace(target, replacement)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(new_content)

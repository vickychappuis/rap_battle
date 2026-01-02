# example.py
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
import os
from dotenv import load_dotenv
load_dotenv()

elevenlabs = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY"),
)

track = elevenlabs.music.compose(
    prompt="""Original male rap acapella ONLY. 90 BPM, 4/4. Length: 10 seconds (exact), deliver as one clean take.
Purpose: instant “club-anthem” impact in the first 2 seconds.

Pocket: laid-back, sit slightly behind the beat; strong accents around beats 2 and 4.
Cadence: mostly 8th-notes, with 1 short 16th-note burst (half-bar max). Leave 1 deliberate pause.
Tone: confident, cool, in-control; baritone/low-mid; crisp consonants; clear diction (no mumbling).
Content: 1 chanty hook phrase repeated twice + 1 punchy brag line (PG-13, no slurs).
Ad-libs: 1 subtle “yeah/uh” on the last beat only; optional single word double on the final punchline.
Recording: dry studio acapella, mono, minimal room, light compression, natural breaths.
Negative: do not imitate any real rapper; no melody singing; no reverb/delay; no background vocals beyond the single double/ad-lib.
""",
    music_length_ms=10000,
)

# Save the track to a file
with open("music_output/try_1.mp3", "wb") as f:
    for chunk in track:
        f.write(chunk)

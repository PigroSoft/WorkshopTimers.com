#!/usr/bin/env python3
"""Record the voice-alert clips with Kokoro, an open-weight speech model (Apache-2.0).

Writes voice/<lang>/<phrase>.mp3 for every language Kokoro speaks. Languages it
doesn't speak (German, Russian, Arabic, Korean) fall back to the English clips
in the app. Run it again after changing a phrase.

    pip install kokoro-onnx soundfile "misaki[ja,zh]"   # and ffmpeg on the PATH
    # model files: https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0)
    python3 scripts/make_voices.py path/to/kokoro-v1.0.onnx path/to/voices-v1.0.bin
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "voice"

# app language -> (Kokoro voice, espeak language, phrases)
VOICES = {
    "en": ("af_heart", "en-us", {
        "s30": "Attention please. Thirty seconds remaining.",
        "m2": "Attention please. Two minutes remaining.",
        "half": "Attention please. Time to switch.",
        "on": "Voice alerts enabled."}),
    "es": ("ef_dora", "es", {
        "s30": "Atención, por favor. Quedan treinta segundos.",
        "m2": "Atención, por favor. Quedan dos minutos.",
        "half": "Atención, por favor. Es hora de cambiar.",
        "on": "Alertas de voz activadas."}),
    "fr": ("ff_siwis", "fr-fr", {
        "s30": "Votre attention, s'il vous plaît. Plus que trente secondes.",
        "m2": "Votre attention, s'il vous plaît. Plus que deux minutes.",
        "half": "Votre attention, s'il vous plaît. C'est le moment de changer.",
        "on": "Alertes vocales activées."}),
    "it": ("if_sara", "it", {
        "s30": "Attenzione, per favore. Mancano trenta secondi.",
        "m2": "Attenzione, per favore. Mancano due minuti.",
        "half": "Attenzione, per favore. È ora di cambiare.",
        "on": "Avvisi vocali attivati."}),
    "pt": ("pf_dora", "pt-br", {
        "s30": "Atenção, por favor. Faltam trinta segundos.",
        "m2": "Atenção, por favor. Faltam dois minutos.",
        "half": "Atenção, por favor. Hora de trocar.",
        "on": "Alertas de voz ativados."}),
    "hi": ("hf_alpha", "hi", {
        "s30": "कृपया ध्यान दें। तीस सेकंड बचे हैं।",
        "m2": "कृपया ध्यान दें। दो मिनट बचे हैं।",
        "half": "कृपया ध्यान दें। बदलने का समय हो गया है।",
        "on": "आवाज़ अलर्ट चालू हो गए हैं।"}),
    "ja": ("jf_alpha", "ja", {
        "s30": "お知らせします。残り三十秒です。",
        "m2": "お知らせします。残り二分です。",
        "half": "お知らせします。交代の時間です。",
        "on": "音声アラートをオンにしました。"}),
    "zh": ("zf_xiaobei", "cmn", {
        "s30": "请注意，还剩三十秒。",
        "m2": "请注意，还剩两分钟。",
        "half": "请注意，该交换了。",
        "on": "语音提醒已开启。"}),
}


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    kokoro = Kokoro(sys.argv[1], sys.argv[2])
    # Japanese and Chinese need Kokoro's own pronunciation library (misaki);
    # the generic one reads kanji letter by letter
    from misaki import ja, zh
    g2p = {"ja": ja.JAG2P(), "zh": zh.ZHG2P()}
    with tempfile.TemporaryDirectory() as tmp:
        for lang, (voice, espeak, phrases) in VOICES.items():
            (OUT / lang).mkdir(parents=True, exist_ok=True)
            for key, text in phrases.items():
                if lang in g2p:
                    ps = g2p[lang](text)
                    ps = ps if isinstance(ps, str) else ps[0]
                    samples, rate = kokoro.create(ps, voice=voice, speed=0.95, is_phonemes=True)
                else:
                    samples, rate = kokoro.create(text, voice=voice, speed=0.95, lang=espeak)
                wav = Path(tmp) / f"{lang}-{key}.wav"
                sf.write(wav, samples, rate)
                mp3 = OUT / lang / f"{key}.mp3"
                # trim silence, even out loudness for a room, small mono MP3
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
                                "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                                "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                                "loudnorm=I=-14:TP=-1.5:LRA=7",
                                "-ar", "24000", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "40k", str(mp3)],
                               check=True)
                print(f"{lang}/{key}.mp3  {mp3.stat().st_size // 1024} KB  {len(samples) / rate:.1f}s")


if __name__ == "__main__":
    main()

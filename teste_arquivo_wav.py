import sys
from vosk import Model, KaldiRecognizer
import wave

wf = wave.open("seuarquivo.wav", "rb")
if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() not in (16000, 8000):
    print("Arquivo deve ser mono PCM 16-bits, 1 canal, taxa 16000Hz (ou compatível).")
    sys.exit(1)

model = Model("/home/big/Área de Trabalho/Athena/_VOZES/vosk-model-pt-fb-v0.1.1-20220516_2113/")  # ex: ~/vosk-model-pt-br
rec = KaldiRecognizer(model, wf.getframerate())

while True:
    data = wf.readframes(4000)
    if len(data) == 0:
        break
    if rec.AcceptWaveform(data):
        print(rec.Result())
    else:
        print(rec.PartialResult())

print(rec.FinalResult())


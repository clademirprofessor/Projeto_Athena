# Carlos Amorim - 2025 - Projeto Athena
# Teste de reconhecimento de voz usando Vosk sem arquivo WAV, capturando áudio do microfone

#TESTE: FUNCIONA SEM UTILIDADE PRÁTICA NO MOMENTO
#FAZER: INTEGRAR COM O PROJETO ATHENA UTILIZANDO A SAÍDA DE TEXTO RECONHECIDO PARA ENVIAR AO ARDUINO

#BIBLIOTECAS NECESSÁRIAS:
#python -m pip install --upgrade pip

#pip install vosk sounddevice numpy

#sudo apt install -y build-essential libsndfile1 portaudio19-dev python3-dev
#MODELO MAIOR BAIXADO DE link: (1,6gB)
#/home/big/Área de Trabalho/Athena/_VOZES/vosk-model-pt-fb-v0.1.1-20220516_2113/

import queue
import sys
from vosk import Model, KaldiRecognizer
import sounddevice as sd

MODEL_PATH = "/home/big/Área de Trabalho/Athena/_VOZES/vosk-model-pt-fb-v0.1.1-20220516_2113/"  # ajuste o caminho do modelo
SAMPLE_RATE = 16000
CHANNELS = 1

q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        # pequeno log de status
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def main():
    try:
        model = Model(MODEL_PATH)
    except Exception as e:
        print("Erro ao carregar o modelo:", e, file=sys.stderr)
        sys.exit(1)

    rec = KaldiRecognizer(model, SAMPLE_RATE)

    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16',
                               channels=CHANNELS, callback=callback):
            print("Gravando do microfone. Pressione Ctrl+C para sair.")
            while True:
                data = q.get()
                if rec.AcceptWaveform(data):
                    print(rec.Result())
                else:
                    print(rec.PartialResult())
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário")
    except Exception as e:
        print("Erro de áudio:", e, file=sys.stderr)

if __name__ == "__main__":
    main()
# ...existing code...

#!/bin/bash

# Atualiza a lista de pacotes e instala o Python 3 e o venv, se ainda não estiverem instalados
sudo apt-get update

# Instala o FFmpeg, necessário para manipulação de arquivos de áudio e vídeo
sudo apt-get install ffmpeg -y
# Instala o libasound2-dev, necessário para o PyAudio funcionar corretamente
sudo apt-get install libasound2-dev -y
# Instala o portaudio19-dev, necessário para o PyAudio funcionar corretamente
sudo apt-get install portaudio19-dev -y
# Instala o libffi-dev, necessário para algumas bibliotecas Python funcionarem corretamente
sudo apt-get install libffi-dev -y
# Instala o libssl-dev, necessário para algumas bibliotecas Python funcionarem corretamente
sudo apt-get install libssl-dev -y
# Instala o build-essential, necessário para compilar algumas bibliotecas Python
sudo apt-get install build-essential -y     


sudo apt-get install python3 python3-venv python3-pip -y
# Cria um diretório para o ambiente virtual
mkdir -p ~/athena_voz_ambiente_virtual
cd ~/athena_voz_ambiente_virtual
# Cria o ambiente virtual
python3 -m venv venv
# Ativa o ambiente virtual
source venv/bin/activate
# Instala o PyAudio e suas dependências no sistema operacional


sudo apt install python3-pyaudio


#dentro do ambiente virtual, execute:

#PyAudio: biblioteca para trabalhar com áudio em Python. Será utilizada para capturar e reproduzir áudio.
pip install PyAudio
#pyttsx3: biblioteca para conversão de texto em fala (text-to-speech) em Python.
pip install pyttsx3

#pyserial: biblioteca para comunicação serial em Python. Será utilizada para comunicação com dispositivos via portas seriais.
#comunicacao com Arduino para executar ações físicas
pip install pyserial

#gTTS: biblioteca que utiliza o Google Text-to-Speech para converter texto em fala.
pip install gTTS
#SpeechRecognition: biblioteca para reconhecimento de fala em Python.
pip install SpeechRecognition

#Instala outras bibliotecas úteis
pip install numpy
pip install requests
pip install Flask
pip install Flask-SocketIO
pip install eventlet
pip install transformers
pip install torch
pip install soundfile
pip install pydub
pip install librosa
pip install scikit-learn
pip install matplotlib
pip install seaborn
pip install pandas
pip install nltk
pip install spacy
pip install opencv-python
pip install moviepy
pip install youtube-dl
pip install ffmpeg-python
pip install Pillow
pip install jupyterlab
pip install notebook
# Informa o usuário que o ambiente virtual foi criado e ativado
echo "Ambiente virtual criado e ativado em ~/athena_voz_ambiente_virtual/venv"
echo "Para ativar o ambiente virtual no futuro, execute: source ~/athena_voz_ambiente_virtual/venv/bin/activate"
# Fim do script


# Desativa o ambiente virtual (opcional)
# deactivate

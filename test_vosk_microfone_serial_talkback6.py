#pip install vosk sounddevice numpy pyserial

import sys
import os
import subprocess
import tempfile
import shutil
import socket
import configparser
from enum import Enum, auto

# Limite de uso de RAM pelo modelo (MB) — altere conforme necessário
MODEL_RAM_THRESHOLD_MB = 700  # 700 MB

# Verificar dependências obrigatórias
REQUIRED_MODULES = {
    'vosk': 'vosk',
    'sounddevice': 'sounddevice',
    'numpy': 'numpy',
    'serial': 'pyserial'
}

missing_modules = []
for module, pip_name in REQUIRED_MODULES.items():
    try:
        __import__(module)
    except ImportError:
        missing_modules.append(f"{module} (pip install {pip_name})")

if missing_modules:
    print("Erro: Módulos obrigatórios não encontrados:")
    for module in missing_modules:
        print(f"  - {module}")
    print("\nInstale os módulos faltantes e tente novamente.")
    sys.exit(1)

# Importar módulos após verificação
import queue
import json
import time
from vosk import Model, KaldiRecognizer
import sounddevice as sd
import serial

class TtsMode(Enum):
    OFFLINE = auto()  # espeak/espeak-ng
    ONLINE = auto()   # gTTS
    AUTO = auto()     # try online first, fallback to offline

# Ajuste conforme seu ambiente
FULL_MODEL_DIR = os.path.expanduser("~/Athena/_VOZES/vosk-model-pt-fb-v0.1.1-20220516_2113")
SMALL_MODEL_DIR = os.path.expanduser("~/Athena/_VOZES/vosk-model-small-pt-0.3")
SAMPLE_RATE = 16000
CHANNELS = 1

# Porta serial do Arduino (ex: /dev/ttyACM0, /dev/ttyUSB0) e baudrate
SERIAL_PORT = "/dev/ttyUSB0"
BAUDRATE = 9600
SERIAL_TIMEOUT = 1.0  # segundos

# Tempo máximo para esperar resposta do Arduino (segundos)
SERIAL_RESPONSE_TIMEOUT = 5.0

# Lista de comandos válidos (tudo em minúsculas)
VALID_COMMANDS = [
    "liga",
    "desliga",
    "ligue",
    "desligue",
    "ligar",
    "desligar",
    "teste",
    "ligar led",
    "desligar led",
    "ligar luz",
    "desligar luz",
    "avancar",
    "parar",
    "girar esquerda",
    "girar direita",
    "girar cabeca",
    "girar cabeça",
    "gira cabeça",
    "girar a cabeça",
    "gira a cabeça",
    "gire a cabeça",
    "ajuda",
    "ajudar",
    "socorro",
    "help",
    "ajuda do cliente", "ajuda do enviador", "ajuda do python"
]

q = queue.Queue()

def callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    q.put(bytes(indata))

def normalize_text(s: str) -> str:
    # Normalização simples: minusculas e strip
    return s.strip().lower()

def get_available_memory_mb():
    """Retorna memória disponível em MB (usa /proc/meminfo)"""
    try:
        with open("/proc/meminfo", "r") as f:
            data = f.read()
        for line in data.splitlines():
            if line.startswith("MemAvailable:"):
                parts = line.split()
                # valor em kB
                kb = int(parts[1])
                return kb // 1024
        # fallback para MemTotal
        for line in data.splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                kb = int(parts[1])
                return kb // 1024
    except Exception:
        pass
    return None

def get_process_rss_mb():
    """Retorna o RSS (resident set size) do processo atual em MB lendo /proc/self/status."""
    try:
        with open("/proc/self/status", "r") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    # valor em kB
                    kb = int(parts[1])
                    return kb // 1024
    except Exception:
        pass
    return None

# Tentar usar psutil para informações do sistema, fallback para /proc
try:
    import psutil  # opcional; se não existir, usamos fallback
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False

#para debug:
#_HAS_PSUTIL = False

def _cpu_percent_fallback(interval=0.1):
    """Calcula uso de CPU percentual lendo /proc/stat (fallback se psutil não existir)."""
    try:
        def _read():
            with open("/proc/stat", "r") as f:
                parts = f.readline().split()[1:]
                parts = list(map(int, parts))
                idle = parts[3]
                total = sum(parts)
                return idle, total
        idle1, total1 = _read()
        time.sleep(interval)
        idle2, total2 = _read()
        idle_delta = idle2 - idle1
        total_delta = total2 - total1
        if total_delta == 0:
            return None
        cpu_pct = 100.0 * (1.0 - (idle_delta / total_delta))
        return round(cpu_pct, 1)
    except Exception:
        return None

def get_system_usage(interval_cpu=0.1):
    """
    Retorna dicionário com uso de CPU (%) e memória (MB).
    Usa psutil se disponível, caso contrário usa /proc.
    """
    # memória (fallback usa get_available_memory_mb)
    avail_mb = get_available_memory_mb()
    total_mb = None
    free_mb = None
    percent = None
    used_mb = None

    if _HAS_PSUTIL:
        try:
            vm = psutil.virtual_memory()
            # psutil -> bytes, converter para MB
            avail_mb = vm.available // (1024 * 1024)
            total_mb = vm.total // (1024 * 1024)
            free_mb = vm.free // (1024 * 1024)
            used_mb = vm.used // (1024 * 1024)
            percent = vm.percent  # já em %
        except Exception:
            pass
    else:
        # fallback para MemTotal (kB -> MB)
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        total_mb = int(line.split()[1]) // 1024
                        break
        except Exception:
            pass

    # cpu
    cpu_pct = None
    if _HAS_PSUTIL:
        try:
            cpu_pct = psutil.cpu_percent(interval=interval_cpu)
        except Exception:
            cpu_pct = _cpu_percent_fallback(interval=interval_cpu)
    else:
        cpu_pct = _cpu_percent_fallback(interval=interval_cpu)

    return {
        "cpu_percent": cpu_pct,
        "avail_mb": avail_mb,
        "free_mb": free_mb,
        "percent": percent,
        "used_mb": used_mb,
        "total_mb": total_mb,
        "rss_mb": get_process_rss_mb()
    }

def prompt_yes_no(msg, default_no=True):
    """Prompt simples sim/não. Retorna True se sim."""
    default = "N" if default_no else "Y"
    ans = input(f"{msg} [y/N]: ").strip().lower()
    return ans in ("y", "yes")

def choose_model():
    """Escolhe entre modelo leve e completo conforme existência e RAM disponível"""
    small_exists = os.path.isdir(SMALL_MODEL_DIR)
    full_exists = os.path.isdir(FULL_MODEL_DIR)

    avail_mb = get_available_memory_mb()
    if avail_mb is not None:
        print(f"Memória disponível: {avail_mb} MB")
    else:
        print("Não foi possível determinar memória disponível (não /proc/meminfo).")

    if full_exists and small_exists:
        print("Ambos os modelos foram encontrados:")
        print(f"  1) Leve:  {SMALL_MODEL_DIR} (~31MB)")
        print(f"  2) Completo: {FULL_MODEL_DIR} (~1.6GB)")
        choice = input("Escolha modelo [1=leve, 2=completo] (padrão 1): ").strip() or "1"
        if choice == "2":
            # Aviso de memória para modelo completo
            if avail_mb is not None and avail_mb < MODEL_RAM_THRESHOLD_MB:
                confirm = input(f"Atenção: memória disponível ~{avail_mb}MB < {MODEL_RAM_THRESHOLD_MB}MB. Modelo completo pode não caber na RAM. Confirmar uso do completo? [y/N]: ").strip().lower()
                if confirm not in ("y", "yes"):
                    print("Usando modelo leve por segurança.")
                    return SMALL_MODEL_DIR
            return FULL_MODEL_DIR
        else:
            return SMALL_MODEL_DIR
    elif full_exists:
        print("Apenas o modelo completo foi encontrado.")
        if avail_mb is not None and avail_mb < MODEL_RAM_THRESHOLD_MB:
            confirm = input(f"Atenção: memória disponível ~{avail_mb}MB < {MODEL_RAM_THRESHOLD_MB}MB. Modelo completo pode não caber na RAM. Deseja prosseguir? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                print("Abortando por insuficiência de RAM.")
                sys.exit(1)
        return FULL_MODEL_DIR
    elif small_exists:
        print("Apenas o modelo leve foi encontrado. Usando o modelo leve.")
        return SMALL_MODEL_DIR
    else:
        print("Erro: nenhum modelo Vosk encontrado.")
        print(f"Coloque um dos modelos em:\n  - Leve: {SMALL_MODEL_DIR}\n  - Completo: {FULL_MODEL_DIR}")
        print("Ou execute o script de configuração para baixar os modelos.")
        sys.exit(1)

def load_model_and_measure(model_path):
    """
    Carrega o modelo Vosk e mede o aumento de uso de RAM (RSS) do processo.
    Se o aumento ultrapassar MODEL_RAM_THRESHOLD_MB, pede confirmação ao usuário.
    """
    rss_before = get_process_rss_mb()
    if rss_before is not None:
        print(f"RSS antes do carregamento do modelo: {rss_before} MB")
    else:
        print("Não foi possível determinar RSS antes do carregamento.")

    try:
        model = Model(model_path)
    except Exception as e:
        print(f"Erro: Não foi possível carregar o modelo de linguagem em '{model_path}'")
        print(f"Detalhes: {e}")
        sys.exit(1)

    rss_after = get_process_rss_mb()
    if rss_after is not None:
        print(f"RSS após carregamento do modelo: {rss_after} MB")
        if rss_before is not None:
            delta = rss_after - rss_before
            print(f"Aumento de memória estimado pelo modelo: {delta} MB")
        else:
            delta = None
    else:
        print("Não foi possível determinar RSS após o carregamento.")
        delta = None

    if delta is not None and delta > MODEL_RAM_THRESHOLD_MB:
        print(f"Atenção: o modelo parece usar ~{delta} MB, acima do limite definido ({MODEL_RAM_THRESHOLD_MB} MB).")
        if not prompt_yes_no("Deseja prosseguir mesmo assim?", default_no=True):
            print("Abortando por solicitação do usuário devido ao uso de memória.")
            sys.exit(1)

    return model

def open_serial():
    """Tenta abrir conexão serial com Arduino"""
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=SERIAL_TIMEOUT)
        time.sleep(2.0)  # Tempo para Arduino reiniciar
        print(f"Conectado ao Arduino em {SERIAL_PORT} @ {BAUDRATE}")
        return ser
    except serial.SerialException as e:
        print(f"Erro: Não foi possível conectar ao Arduino em {SERIAL_PORT}")
        print(f"Detalhes: {str(e)}")
        print("\nVerifique se:")
        print("1. O Arduino está conectado na porta correta")
        print("2. Você tem permissão para acessar a porta (sudo adduser $USER dialout)")
        print("3. Nenhum outro programa está usando a porta")
        sys.exit(1)

def has_internet(host="8.8.8.8", port=53, timeout=2):
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except Exception:
        return False

def _play_audio_file(path):
    """Tenta reproduzir um arquivo de áudio com ffplay/mpg123/aplay (com conversão)."""
    ffplay = shutil.which("ffplay")
    mpg123 = shutil.which("mpg123")
    aplay = shutil.which("aplay")
    ffmpeg = shutil.which("ffmpeg") or shutil.which("avconv")

    if ffplay:
        subprocess.run([ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet", path])
        return True
    if mpg123:
        subprocess.run([mpg123, "-q", path])
        return True
    if aplay and ffmpeg and path.lower().endswith(".mp3"):
        # converter mp3 -> wav temporário e tocar com aplay
        wav = tempfile.mktemp(suffix=".wav")
        subprocess.run([ffmpeg, "-y", "-i", path, wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([aplay, wav], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            os.remove(wav)
        except Exception:
            pass
        return True
    return False

# Configuration with defaults
CONFIG_FILE = os.path.expanduser("~/Athena/config.ini")
DEFAULT_TTS_MODE = TtsMode.AUTO

def load_tts_config():
    """Load TTS configuration from file or create with defaults"""
    config = configparser.ConfigParser()
    
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    else:
        config['TTS'] = {
            'mode': DEFAULT_TTS_MODE.name,  # OFFLINE, ONLINE, or AUTO
        }
        # Ensure directory exists
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
    
    # Validate mode
    try:
        return TtsMode[config['TTS']['mode'].upper()]
    except (KeyError, ValueError):
        return DEFAULT_TTS_MODE

def save_tts_config(mode: TtsMode):
    """Save TTS configuration to file"""
    config = configparser.ConfigParser()
    config['TTS'] = {'mode': mode.name}
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)

def speak(text: str, mode: TtsMode = None):
    """
    Fala o texto usando o modo especificado ou configurado
    mode: OFFLINE (espeak), ONLINE (gTTS) ou AUTO (tenta online, fallback offline)
    """
    if mode is None:
        mode = load_tts_config()
    
    text = str(text).strip()
    if not text:
        return

    # Se modo AUTO ou ONLINE, tenta gTTS primeiro
    if mode in (TtsMode.AUTO, TtsMode.ONLINE):
        if has_internet():
            try:
                from gtts import gTTS
                tmp_mp3 = tempfile.mktemp(suffix=".mp3")
                tts = gTTS(text=text, lang="pt-br")
                tts.save(tmp_mp3)
                played = _play_audio_file(tmp_mp3)
                try:
                    os.remove(tmp_mp3)
                except Exception:
                    pass
                if played:
                    return
            except Exception as e:
                if mode == TtsMode.ONLINE:
                    print(f"Erro TTS online: {e}")
                    return
                # em modo AUTO, continua para offline
    
    # Modo OFFLINE ou fallback de AUTO
    if mode in (TtsMode.AUTO, TtsMode.OFFLINE):
        espeakng = shutil.which("espeak-ng")
        espeak = shutil.which("espeak")
        if espeakng:
            subprocess.run([espeakng, "-v", "pt-br+f2", text])
            return
        if espeak:
            subprocess.run([espeak, "-v", "pt-br+f2", text])
            return
    
    # Nenhum método disponível
    print(f"[TTS indisponível] {text}")

def configure_tts():
    """Interface para configurar modo TTS"""
    current_mode = load_tts_config()
    print("\nConfiguração do Sistema de Fala")
    print("-" * 30)
    print(f"Modo atual: {current_mode.name}")
    print("\nModos disponíveis:")
    print("1. OFFLINE - Usa espeak/espeak-ng (funciona sem internet)")
    print("2. ONLINE  - Usa Google TTS (requer internet, melhor qualidade)")
    print("3. AUTO    - Tenta online, usa offline se falhar")
    
    while True:
        choice = input("\nEscolha o modo (1-3) ou Enter para manter atual: ").strip()
        if not choice:
            return current_mode
        
        if choice == "1":
            mode = TtsMode.OFFLINE
            break
        elif choice == "2":
            mode = TtsMode.ONLINE
            break
        elif choice == "3":
            mode = TtsMode.AUTO
            break
        else:
            print("Opção inválida!")
    
    save_tts_config(mode)
    return mode

def try_send_serial(ser, text):
    """
    Envia comando para Arduino, espera resposta e fala resultado.
    Retorna True quando completar todo o ciclo.
    """
    if text in ("ajuda do cliente", "ajuda do enviador", "ajuda do python"):
        help_text = "Os comandos disponíveis no enviador são: " + ", ".join(sorted(set(VALID_COMMANDS)))
        print(help_text)
        speak(help_text)
        return True

    if ser is None:
        sim_msg = f"Simulado: enviar para serial: '{text}'"
        print(sim_msg)
        speak(sim_msg)
        time.sleep(1)  # simula tempo de execução
        return True
    try:
        #limpar buffer antes de enviar
        ser.reset_input_buffer()

        print(f"Enviado para serial: '{text}'")
        ser.write((text + "\n").encode("utf-8"))
        ser.flush()

        # esperar resposta até timeout
        start = time.time()
        resp = b""
        while time.time() - start < SERIAL_RESPONSE_TIMEOUT:
            if ser.in_waiting:

               line = ser.readline()
               #if not line:
                    # readline respeita timeout; se vazio, continuar tentanto até timeout
                    #continue
               if line:
                   resp += line


                   # se linha termina com newline, assumir fim
                   if resp.endswith(b"\n") or resp.endswith(b"\r\n"):
                    break
            time.sleep(0.1) #pequena pausa para evitar busy wait    para não sobrecarregar CPU   
        # 3. processa resposta  

        if resp:
            try:
                resp_text = resp.decode("utf-8", errors="replace").strip()
                print(f"Resposta Arduino: {resp_text}")
                # 4. Fala a resposta
                speak(resp_text)
                # 5. Espera a fala terminar (depende do backend TTS)
                if _HAS_PSUTIL:
                    # Espera processo do TTS terminar se usando espeak/espeak-ng
                    procs = [p for p in psutil.process_iter(['name']) 
                            if p.info['name'] in ('espeak', 'espeak-ng')]
                    for p in procs:
                        try:
                            p.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            pass
                return True
            except Exception as e:
                print(f"Erro ao processar resposta: {e}")
                speak("Erro ao processar resposta do Arduino")
        else:
            print("Timeout esperando resposta do Arduino")
            speak("Arduino não respondeu a tempo")
        return False #precisou tentar, mas falhou 
    


    except Exception as e:
        print(f"Erro ao enviar para serial: {e}", file=sys.stderr)
        speak("Erro ao comunicar com o Arduino.")
    return False

def check_arduino_communication(ser):
    """Verifica comunicação inicial com Arduino"""
    if ser is None:
        print("Modo simulação: sem verificação de comunicação")
        return True
    
    try:
        # Limpa buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Envia comando de teste
        print("Verificando comunicação com Arduino...")
        ser.write(b"teste_comunicacao\n")
        ser.flush()
        
        # Espera resposta com timeout
        start = time.time()
        while (time.time() - start) < SERIAL_RESPONSE_TIMEOUT:
            if ser.in_waiting:
                response = ser.readline().decode('utf-8').strip()
                if response == "Comunicação estabelecida com sucesso":
                    print("Arduino respondeu corretamente!")
                    speak("Comunicação com Arduino estabelecida")
                    return True
        
        print("Erro: Arduino não respondeu ao teste de comunicação")
        speak("Erro de comunicação com Arduino")
        return False
            
    except Exception as e:
        print(f"Erro ao verificar comunicação: {e}")
        return False

def main():
    # Escolher modelo conforme existência e RAM
    selected_model_path = choose_model()
    print(f"Modelo selecionado: {selected_model_path}")

    # Verificar e carregar modelo (carrega e mede RAM)
    model = load_model_and_measure(selected_model_path)
    
    # Verificar conexão Arduino
    ser = open_serial()
    if not check_arduino_communication(ser):
        print("Abortando devido a falha na comunicação")
        sys.exit(1)
    
    # Continua com reconhecimento de voz
    rec = KaldiRecognizer(model, SAMPLE_RATE)

    try:
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16',
                             channels=CHANNELS, callback=callback):
            print("\nSistema pronto!")
            print("Gravando do microfone. Pressione Ctrl+C para sair.")
            print("\nComandos reconhecidos:")
            for cmd in VALID_COMMANDS:
                print(f"  - {cmd}")
            print("")

            while True:
                data = q.get()
                if rec.AcceptWaveform(data):
                    # Resultado final parcial (por bloco)
                    j = json.loads(rec.Result())
                    text = normalize_text(j.get("text", ""))
                    if not text:
                        continue

                    # obter uso do sistema / mostrar antes de enviar ao Arduino
                    usage = get_system_usage(interval_cpu=0.05)
                    cpu_str = f"{usage['cpu_percent']}%" if usage['cpu_percent'] is not None else "N/A"
                    avail_str = f"{usage['avail_mb']} MB" if usage['avail_mb'] is not None else "N/A"
                    free_str = f"{usage['free_mb']} MB" if usage['free_mb'] is not None else "N/A"
                    percent_str = f"{usage['percent']}%" if usage['percent'] is not None else "N/A"
                    used_str = f"{usage['used_mb']} MB" if usage['used_mb'] is not None else "N/A"
                    total_str = f"{usage['total_mb']} MB" if usage['total_mb'] is not None else "N/A"
                    rss_str = f"{usage['rss_mb']} MB" if usage['rss_mb'] is not None else "N/A"

                    print(f"Final (bloco): {text}")
                    print(f"Uso sistema -> CPU: {cpu_str} | Mem disponível: {avail_str} | Livre: {free_str} | Percentual: {percent_str} | Usado: {used_str} | Total: {total_str} | RSS processo: {rss_str}")

                    
                    if text in VALID_COMMANDS:
                        # Aguarda ciclo completo antes de continuar
                        if try_send_serial(ser, text):
                            print("\nPronto para novo comando (linha 602) ...")
                        else:
                            print("\nErro no último comando. (linha 604) Pronto para tentar novamente...")
                    else:
                        print("Comando não reconhecido como válido.")
                else:
                    # Exibe parcial (opcional)
                    j = json.loads(rec.PartialResult())
                    partial = normalize_text(j.get("partial", ""))
                    if partial:
                        print("Parcial:", partial, end="\r")
    except KeyboardInterrupt:
        print("\nInterrompido pelo usuário")
    except Exception as e:
        print("Erro de áudio:", e, file=sys.stderr)
    finally:
        # Ao finalizar, envie o resultado final restante
        try:
            j = json.loads(rec.FinalResult())
            text = normalize_text(j.get("text", ""))
            if text:
                # mostrar uso do sistema na última sentença
                usage = get_system_usage(interval_cpu=0.05)
                cpu_str = f"{usage['cpu_percent']}%" if usage['cpu_percent'] is not None else "N/A"
                avail_str = f"{usage['avail_mb']} MB" if usage['avail_mb'] is not None else "N/A"
                total_str = f"{usage['total_mb']} MB" if usage['total_mb'] is not None else "N/A"
                rss_str = f"{usage['rss_mb']} MB" if usage['rss_mb'] is not None else "N/A"

                print("Final (final):", text)
                print(f"Uso sistema -> CPU: {cpu_str} | Mem disponível: {avail_str} / {total_str} | RSS processo: {rss_str}")

                if text in VALID_COMMANDS:
                    # Aguarda ciclo completo antes de continuar
                    if try_send_serial(ser, text):
                        print("\nPronto para novo comando (linha 636) ...")
                    else:
                        print("\nErro no último comando. (linha 638) Pronto para tentar novamente...")
                else:
                    print("Comando não reconhecido como válido.")

        except Exception:
            pass
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()

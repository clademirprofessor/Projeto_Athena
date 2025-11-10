import speech_recognition as sr
import serial
import time
import pyttsx3  # Para fala

# Configurar comunicação serial com o Arduino
#arduino = serial.Serial('COM3', 9600)  # Altere para a porta correta do seu Arduino
arduino = serial.Serial('/dev/ttyUSB0', 9600)  # Altere para a porta correta do seu Arduino
time.sleep(2)  # Esperar o Arduino iniciar

# Inicializar reconhecimento de voz e motor de fala
recognizer = sr.Recognizer()
engine = pyttsx3.init()

def speak(message):
    print(message)
    engine.say(message)
    engine.runAndWait()

speak("FALE ALGUMA COISA...")

while True:
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source)
            command = recognizer.recognize_google(audio).lower()
            speak("VOCE FALOU: " + command)

            # Comandos reconhecidos
            if "led on" in command:
                arduino.write(b"ON\n")
                speak("Turning LED on")
            elif "led off" in command:
                arduino.write(b"OFF\n")
                speak("Turning LED off")
            elif "exit" in command:
                speak("Exiting program")
                break
            else:
                speak("COMANDO NAO RECONHECIDO")

    except sr.UnknownValueError:
        speak("Sorry, I could not understand the audio.")
    except sr.RequestError:
        speak("Could not connect to the internet. Please check your connection.")

arduino.close()

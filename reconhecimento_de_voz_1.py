import speech_recognition as sr
import serial
import time

# Set up serial communication
arduino = serial.Serial('COM3', 9600)  # Change COM3 to your Arduino port
time.sleep(2)  # Wait for Arduino to initialize

# Initialize recognizer
recognizer = sr.Recognizer()

print("Say something...")

while True:
    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source)
            command = recognizer.recognize_google(audio).lower()
            print("You said:", command)

            # Check for specific commands
            if "led on" in command:
                arduino.write(b"ON\n")
            elif "led off" in command:
                arduino.write(b"OFF\n")
            elif "exit" in command:
                print("Exiting...")
                break
            else:
                print("Unknown command")

    except sr.UnknownValueError:
        print("Sorry, could not understand audio")
    except sr.RequestError:
        print("Could not request results; check your internet connection")

arduino.close()



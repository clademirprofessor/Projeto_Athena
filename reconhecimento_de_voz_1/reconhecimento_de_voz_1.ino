//ARDUINO MEGA COM DISPLAY 2.4" TFT CLD SHIELD
//SE VOCE ENTENDER ISSO IMPLEMENTE A EXIBIÇÃO DA MENSAGEM RECEBIDA PELA SERIAL NO DISPLAY :)
//LCD_RO  A0
//LCD_WR  A1
//LCD_RS  A2
//LCD_CS  A3
//LCD_RST A4
//LCD_D0  D8
//LCD_D1  D9
//LCD_D2  D2 ... LCD_D7 D7

// Definições de pinos (ajuste conforme sua montagem)
const int LED_PIN = 13;

void setup() {
  Serial.begin(9600);
  while (!Serial) {
    ; // Espera porta serial conectar
  }
  pinMode(LED_PIN, OUTPUT);
  Serial.println("Arduino pronto!");
}

void loop() {
  if (Serial.available()) {
    String comando = Serial.readStringUntil('\n');
    comando.trim();
    comando.toLowerCase();

    // Verificação inicial de comunicação
    if (comando == "teste_comunicacao") {
      Serial.println("Comunicação estabelecida com sucesso");
      return;
    }

    // Processar outros comandos
    if (comando == "ligar led" || comando == "liga" || comando == "ligar" || comando == "ligue") {
      digitalWrite(LED_PIN, HIGH);
      Serial.println("LED ligado com sucesso");
    }
    else if (comando == "desligar led" || comando == "desliga" || comando == "desligar" || comando == "desligue") {
      digitalWrite(LED_PIN, LOW);
      Serial.println("LED desligado com sucesso");
    }
    else if (comando == "avancar") {
      // Código para avançar
      Serial.println("Robô avançando");
    }
    else if (comando == "parar") {
      // Código para parar
      Serial.println("Robô parado");
    }
    else if (comando == "girar esquerda") {
      // Código para girar
      Serial.println("Girando para esquerda");
    }
    else if (comando == "girar direita") {
      // Código para girar
      Serial.println("Girando para direita");
    }
    else if (comando == "girar cabeca" || comando == "gira cabeça" || comando == "gira a cabeça" || comando == "girar cabeça" || comando == "girar a cabeça" || comando == "gire a cabeça") {
      Serial.println("Girando a cabeça no giro do exorcista!");
    }
    else if (comando == "ajuda" || comando == "ajudar" || 
             comando == "socorro" || comando == "help") {
      Serial.println("Comandos disponíveis: ligar led, desligar led, liga, desliga, "
                    "avançar, parar, girar esquerda, girar direita, girar cabeça, "
                    "ajuda, socorro, help");
    }
    else {
      Serial.print("Comando não reconhecido: ");
      Serial.println(comando);
    }
  }
}

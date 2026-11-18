# Ambilight caseiro numa TV TCL Google TV

Fita de LED atrás de uma TV TCL 55" (Google TV, Android 12, chip Amlogic) que acompanha as cores da imagem,
sem câmera, sem root e sem caixa HDMI. A própria TV captura a tela e manda as cores pelo Wi-Fi para um ESP32
com [WLED](https://kno.wled.ge/).

```
TV (app Universal Ambient Light) --Wi-Fi, DDP porta 4048--> ESP32 (WLED) --GPIO16--> fita WS2812B (220 LEDs)
```

- **Funciona em:** SmartTube (YouTube) e Stremio com player externo. Os dois desenham o vídeo pela GPU, então a
  captura de tela enxerga a imagem mesmo com decodificação por hardware.
- **Não funciona em:** HDMI. A TCL bloqueia a captura da entrada HDMI (`tcl-screencontrol-cap: PERMISSION_DENIED`).
  O plano para os consoles está em [docs/pendencias.md](docs/pendencias.md).
- **Extras:** animação laranja ao ligar e ao desligar a TV, e controle por voz pela Alexa com a TV desligada.

## Hardware

| Peça | Detalhe |
|---|---|
| Controlador | ESP32 DevKit WROOM-32 (ESP32-D0WD-V3, 4 MB, USB CP2102) |
| Fita | WS2812B 5 V, 60 LEDs/m, IP20, um pixel por LED |
| LEDs na TV | 39 esquerda, 71 topo, 39 direita, 71 embaixo (220), começando embaixo à esquerda, sentido horário |
| Energia hoje | carregador de celular no USB do ESP32; fita pelo pino VIN; limite de 850 mA no WLED |
| Energia final | fonte 5 V 10 A, injeção nas pontas, limite de 8500 mA |

Ligação: dados da fita no **GPIO16 (RX2)**, GND comum, 5 V da fita no **VIN**. Na fonte definitiva entram um
resistor de 330 Ω no dado e um capacitor de 1000 µF na entrada da fita.

## O que tem aqui

| Pasta | Conteúdo |
|---|---|
| [`wled/`](wled/) | `cfg.json` (configuração do WLED, sem a rede) e `presets.json` (animações e luminária) |
| [`ual/configuracoes.md`](ual/configuracoes.md) | todas as opções do app Universal Ambient Light na TV |
| [`tv/ambilight.txt.example`](tv/ambilight.txt.example) | gatilho das animações, lido pelo Free My TV |
| [`tools/`](tools/) | scripts usados nos testes (Wi-Fi por serial, calibração das bordas, simulador de LEDs) |
| [`docs/`](docs/) | guia para montar do zero, pendências e diagrama da arquitetura |

## WLED

Versão 16.0.1, gravada com `esptool`:

```bash
esptool --chip esp32 --port COM<n> write_flash --flash-size 4MB \
  0x1000 bootloader_esp32_8m.bin 0x8000 partitions_c3_4m.bin 0x10000 WLED_16.0.1_ESP32.bin
```

Wi-Fi pelo protocolo Improv na serial: `WIFI_SSID=... WIFI_PASS=... python tools/improv_wifi.py COM<n>`.
O ESP32 só tem 2,4 GHz. A TV pode ficar no 5 GHz, desde que seja a mesma rede.

Pontos da configuração ([`wled/cfg.json`](wled/cfg.json)):
- WS281x, ordem **GRB**, 220 LEDs no GPIO16.
- Gama 2.2, aplicada também ao tempo real.
- Limite de corrente de 850 mA, porque o ESP32 está no USB.
- Integração com a Alexa ligada, com o nome "Luz da TV".

Para restaurar: na interface do WLED, *Config → Security & Updates → Restore*, ou envie o arquivo pela API.
Antes, coloque o nome da sua rede no lugar de `<SEU_WIFI_2.4GHZ>`. A senha do Wi-Fi não fica no arquivo.

### Presets ([`wled/presets.json`](wled/presets.json))

| Nº | Uso |
|---|---|
| 2 | Apagado e devolve o controle à TV (`lor:0`). Fim da abertura |
| 3 | Abertura: sequência com o preset 12 por 3,5 s e depois o 2 |
| 12 | Laranja enchendo a moldura LED por LED (efeito Percent, `lor:2`) |
| 22 | Encerramento: preset 20 (moldura cheia), 23 (recolhe LED por LED) e 21 |
| 21 | Desligado, com branco quente guardado para a Alexa. Também é o preset de boot |
| 11–17 | Outras animações testadas (cometa arco-íris, aurora, fogos...) |

`lor:2` faz o WLED ignorar os dados da TV durante a abertura. No encerramento, `lor:1` ignora só até a TV
parar de mandar, o que ela faz no standby. Assim nada fica travado.

## Animações ao ligar e desligar

A TV usa um [fork do Free My TV](https://github.com/AlekOliveira/free-my-tv-tcl-t800t02) como tela inicial. O
serviço dele que lê o controle fica sempre rodando e escuta "tela ligada" e "tela desligada". Em cada evento,
ele manda um POST para o WLED com o texto de `Android/data/io.freemytv/files/ambilight.txt`:

```bash
adb push tv/ambilight.txt.example /sdcard/Android/data/io.freemytv/files/ambilight.txt
```

(Troque `<IP-DO-ESP32>` antes.) Linha 1: a URL. Linha 2: o JSON de ligar. Linha 3: o de desligar.

O boot do ESP32 não serve de gatilho. No standby, a TV liga e desliga o USB várias vezes, e com a fonte
definitiva o ESP32 nunca reinicia.

## Alexa

Com a integração ligada, o WLED aparece na rede como uma lâmpada Philips Hue. Um Echo na mesma rede acha a
"Luz da TV" em *Descobrir dispositivos*. Ligar, desligar, brilho e cor funcionam por voz. Com a TV ligada, o
vídeo tem prioridade. Com ela desligada, a fita vira luminária.

## Limites encontrados

- O vídeo de players que usam a camada de hardware da Amlogic sai preto na captura: YouTube oficial e Stremio
  com o player interno e decodificação por hardware. Funcionam o SmartTube (com a correção de captura ligada nas
  opções de desenvolvedor do player) e o Stremio com mpv ou Kodi como player externo.
- A entrada HDMI fica bloqueada para captura sem root.
- O IP do ESP32 muda quando o roteador reinicia. É preciso uma reserva de DHCP ou um IP fixo no WLED.

Para montar do zero, veja o [guia](docs/guia-ambilight-diy.md).

## Licença

MIT. Veja [LICENSE](LICENSE).

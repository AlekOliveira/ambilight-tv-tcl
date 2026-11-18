# Ambilight DIY para Android TV / Google TV — guia para o Claude Code

> **Para quem recebeu este arquivo:** abra o Claude Code numa pasta vazia, anexe ou cole este arquivo e escreva:
> *"Leia este guia e me ajude a montar o ambilight na minha TV, um passo por vez."*
> O Claude vai fazer algumas perguntas antes de começar.

---

## Instruções para o Claude

Você vai ajudar uma pessoa a montar um ambilight caseiro: uma fita de LED atrás da TV que copia as cores das bordas da tela. Este guia resume um projeto que já funciona numa TV TCL 55" com Google TV. Adapte tudo para a TV e os equipamentos desta pessoa.

### Como conduzir
- **Um passo por vez.** Dê só o próximo passo, espere a confirmação e então siga.
- **Respostas curtas e diretas.** Nada de textões ou de explicar o que não foi perguntado.
- **Antes de qualquer ligação elétrica:** confira a voltagem e a polaridade, e peça foto quando houver dúvida.
- **Senhas** (Wi-Fi e outras) quem digita é a pessoa, não você.

### Regras de segurança na TV
- Não fazer root, não desbloquear o bootloader e não usar exploits.
- Não desativar a autenticação do ADB.
- Não desinstalar nem desativar apps do sistema sem pedir. Assistentes de voz e serviços do fabricante podem quebrar o controle por voz.
- Manter a aceleração de vídeo por hardware ligada nos players.

### Primeiro, colete estas informações
1. **Marca e modelo da TV**, versão do Android/Google TV e tamanho (polegadas). Com ADB dá para conferir: `getprop ro.product.model`, `getprop ro.build.version.release`.
2. **Medidas da TV** (largura × altura em cm) e **distância até a parede**.
3. **Fontes de vídeo** que ela quer: YouTube, Stremio, Netflix, HDMI (videogame etc.).
4. **O que já tem em casa:** placa ESP32/ESP8266/Arduino, fita de LED (modelo, voltagem, LEDs por metro), fonte, ferro de solda, multímetro.
5. **Rede:** Wi-Fi tem 2,4 GHz? O roteador permite reservar IP (reserva de DHCP)?
6. **PC disponível** (Windows/Mac/Linux) para gravar a placa e usar o ADB.

---

## Arquitetura (o que funciona)

```
TV (app UAL captura a tela) ──Wi-Fi, DDP UDP 4048──▶ ESP32 com WLED ──dados──▶ fita WS2812B 5 V
```

- **UAL — Universal Ambient Light** (vasmarfas, código aberto, na Play Store). Roda na TV, captura a tela (MediaProjection), calcula a cor de cada LED e envia pronto. Suporta WLED (DDP), Adalight (USB) e Hyperion/HyperHDR.
- **WLED** no ESP32: recebe os pacotes e acende a fita. Não faz cálculo nenhum.
- Toda a parte pesada roda na TV. O ESP32 só repassa as cores.
- Para HDMI no futuro dá para pôr um **HyperHDR** no meio (PC ou Raspberry Pi), sem trocar a fita nem o ESP32.

---

## O que a captura consegue ver (testado)

| Fonte | Funciona? | Como |
|---|---|---|
| Menus e apps comuns | sim | direto |
| YouTube | **app oficial sai preto** | usar o **SmartTube**: Configurações > Player > Opções de desenvolvedor > ligar "Luz ambiente / Correção de capturas de tela" |
| Stremio | **player interno sai preto** | player externo: **Kodi** (`videoplayer.usemediacodecsurface=false`, `usemediacodec=true`) ou **mpv-android** |
| Netflix, Prime, Disney+ | não | a proteção DRM bloqueia a captura |
| HDMI (videogame) | não | precisa de splitter HDMI + placa de captura USB + HyperHDR |

Motivo: em vários chips (Amlogic, por exemplo) o vídeo decodificado por hardware vai para uma camada separada que a captura não enxerga. Players que desenham o vídeo pela GPU (SmartTube com a opção acima, Kodi, mpv) ficam visíveis **com a aceleração ligada**.

Primeiro teste, antes de comprar qualquer coisa: instalar o UAL, apontar para o IP do PC e conferir se as cores mudam com o vídeo. Um receptor DDP simples em Python resolve: escutar UDP 4048 e mostrar os bytes RGB a partir do byte 10.

---

## Lista de compras (referência)

| Item | Especificação | Observação |
|---|---|---|
| Placa | **ESP32 DevKit (WROOM-32)**, USB-C | 4 MB de flash. O chip USB costuma ser CP2102 ou CH340 |
| Fita | **WS2812B 5 V, 60 LEDs/m**, IP20 | cada LED é um pixel. Comprimento = perímetro da TV + sobra |
| Fonte | **5 V**, com corrente adequada (ver cálculo) | colmeia (bornes V+/V−) ou Mean Well LRS |
| Conectores | JST SM de 3 pinos | facilita desmontar |
| Recomendado | resistor de 330 Ω no dado, capacitor de 1000 µF na entrada da fita | |
| Opcional | level shifter 74AHCT125 | só se houver piscadas ou cores erradas |

**Cálculos:**
- LEDs = perímetro onde a fita vai (cm) ÷ 100 × 60. Exemplo: TV 55" (~122 × 70 cm), fita uns 3 cm para dentro da borda → cerca de 69 / 38 / 69 / 38 ≈ **214 LEDs**.
- Pior caso de corrente ≈ LEDs × 0,06 A (tudo branco no máximo). 214 LEDs ≈ 12 A. Uma fonte de **5 V 10 A** com o limitador do WLED em uns 8,5 A atende. Em uso normal a fita consome bem menos (10–20 W).
- Consumo típico: cerca de 4 kWh/mês usando 4 h por dia.

---

## Ligação elétrica

```
Fonte 5 V (+) ──┬── 5V da fita (entrada e injeções)
                └── VIN do ESP32
Fonte 5 V (−) ──┬── GND da fita
                └── GND do ESP32          ← GND comum é obrigatório
ESP32 GPIO16 (pino "RX2") ── resistor 330 Ω ── DIN da fita
Capacitor 1000 µF entre 5V e GND na entrada da fita
```

- **Injeção de energia:** em fita longa, ligue 5V/GND também no meio ou no fim, senão as cores ficam amareladas no final.
- **Sentido:** os dados entram pela ponta com a seta apontando para dentro da fita (`DIN`).
- **Curvas:** corte só nas marcas de cobre entre LEDs e solde 3 fios curtos (5V, DO→DIN, GND), com termorretrátil.
- **Nunca** ligue 12 V em nenhum pino do ESP32.
- Os pinos `3V3` e `GND` costumam ficar lado a lado. Cuidado ao encaixar.
- Para testar só a placa, o ESP32 pode ficar no USB do PC ou da TV. Só os dados vão pelo Wi-Fi.

---

## Passo a passo do software

### 1. Driver USB (Windows)
- **CP2102**: driver "CP210x Universal Windows Driver" da Silicon Labs. **CH340**: driver da WCH.
- Gerenciador de Dispositivos com "código 28" = driver não instalado.
- Instalação pelo terminal (como administrador): `pnputil /add-driver silabser.inf /install`. Confira a assinatura antes.

### 2. Gravar o WLED
- **Mais fácil:** https://install.wled.me no Chrome. Modo **Basic** e Install.
- **Pelo esptool**, num ESP32 de 4 MB (layout que o instalador usa):
  ```bash
  python -m esptool --chip esp32 --port COMx erase-flash
  python -m esptool --chip esp32 --port COMx --baud 921600 write-flash --flash-mode dio --flash-size 4MB \
    0x1000 bootloader_esp32_8m.bin 0x8000 partitions_c3_4m.bin 0x10000 WLED_<versão>_ESP32.bin
  ```
  O bootloader e a tabela de partições ficam em `install.wled.me/bin/boot/` e o firmware na release do GitHub `wled/WLED`.

### 3. Wi-Fi do ESP32
- **Só 2,4 GHz.** Se a TV estiver na 5 GHz do mesmo roteador, funciona normal (mesma rede).
- Pelo instalador web: "Configure Wi-Fi". Se a lista vier vazia, digite o nome da rede em "Join other".
- Alternativa: conectar o celular na rede `WLED-AP` (senha padrão `wled1234`), abrir `http://4.3.2.1` e configurar.
- Também dá pelo protocolo **Improv** via serial (script Python). A senha quem digita é a pessoa.

### 4. Configurar o WLED (`http://IP-do-ESP32`)
- Config > LED Preferences: **GPIO 16**, tipo **WS281x**, quantidade de LEDs, ordem de cor (WS2812B costuma ser **GRB**).
- **Limitador de corrente:** coloque o valor real da fonte (ex.: 8500 mA). Com o padrão de 850 mA a fita fica fraca.
- **Brilho:** o padrão é 50% (128). Suba para 255 e salve como brilho de inicialização.
- A API JSON ajuda a automatizar: `POST /json/cfg` (configuração) e `POST /json/state` (estado).

### 5. Configurar o UAL na TV
- Connection: **WLED / DDP**, Host = IP do ESP32, Port **4048**.
- **LED Layout:** LEDs por lado (esquerda/cima/direita/baixo). A ordem padrão começa **embaixo à esquerda e sobe** pela esquerda. A fita física tem que começar no mesmo canto e seguir o mesmo sentido.
- "WLED brightness" em 255.
- Na primeira vez a TV pede permissão de captura de tela: "Iniciar agora".
- Por ADB dá para navegar e digitar: `input tap x y`, `input text 192.168.0.X`, `screencap`. Confira o campo pela captura de tela antes de dar OK, porque às vezes o primeiro caractere se perde.

### 6. Calibrar
- **Ordem das cores:** mande vermelho e depois verde pelo WLED. Se o verde sair azul, por exemplo, troque a ordem (GRB, RGB, BRG…) até bater.
- **Contar pixels:** pinte blocos de 100 com cores diferentes, depois blocos de 10, e por fim acenda um pixel só. Isso também mostra se um chip comanda 1 ou 3 LEDs.
- **Lados certos:** no SmartTube, procure vídeos "ambilight test" e confira se cada borda acende no lado certo.

---

## Problemas que já aconteceram (e a solução)

| Sintoma | Causa | Solução |
|---|---|---|
| Fita preta no YouTube ou no Stremio | camada de vídeo por hardware | SmartTube com a opção de captura; Stremio com Kodi ou mpv externo |
| PC não vê a placa (código 28) | sem driver CP2102/CH340 | instalar o driver; usar cabo USB **de dados** |
| Instalador não abre a porta | porta presa em outra aba ou programa | fechar a aba do instalador ou o monitor serial |
| Rede não aparece no setup do Wi-Fi | busca do Improv vazia | digitar o nome da rede (2,4 GHz) |
| Parou de funcionar depois de reiniciar o roteador | **o IP do ESP32 mudou** | achar pelo MAC (`arp -a` depois de um ping na faixa) e atualizar o host no UAL. Solução definitiva: reserva de DHCP no roteador ou IP fixo no WLED fora da faixa do DHCP |
| Fita fraca | brilho 50% ou limitador em 850 mA | brilho 255 e limitador com o valor real da fonte |
| Cores trocadas | ordem de cor errada | teste de vermelho e verde, depois ajustar a ordem |
| Só um pedaço da tela reflete | quantidade de LEDs no UAL diferente da do WLED | deixar os dois com a mesma quantidade total |
| Página do WLED lenta ou sem resposta | sinal fraco, ou IP antigo apontando para outro aparelho | conferir o sinal em `/json/info` e o IP pelo MAC |

### Fitas antigas de 12 V (WS2811 e compatíveis: UCS1903, GS1903, SM16703)
- Funcionam no WLED como **WS281x**, mas precisam da **fonte de 12 V** delas. A fonte de 5 V não serve.
- O chip fica separado do LED e geralmente **comanda 3 LEDs** (1 pixel = 3 LEDs), então o detalhe é bem menor.
- Controladoras antigas com plug de 4 pinos (`+ DATA CLK −`): o fio CLK não é usado nesse tipo de fita.
- Antes de usar uma entrada de energia sem marcação, **confira a polaridade com multímetro**.

---

## Ideias de evolução
- **USB em vez de Wi-Fi:** Adalight a 921600 baud ou mais, se a TV reconhecer o chip USB. A 115200 o atraso fica pior que no Wi-Fi.
- **HDMI:** splitter (sem perder qualidade na TV) + placa de captura USB + HyperHDR num PC ou Raspberry Pi, com prioridade entre as fontes.
- **Desligar com a TV:** ESP32 no USB da TV, ou tomada inteligente na fonte.

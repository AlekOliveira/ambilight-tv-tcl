# Configurações do Universal Ambient Light (UAL) na TV

App: `com.vasmarfas.UniversalAmbientLight`, versão 2.0.4, numa TV TCL Google TV (Android 12).
O app não exporta as configurações, então elas estão aqui, lidas da tela em 2026-11-18.

## Conexão

| Opção | Valor |
|---|---|
| Protocolo | DDP |
| Host | `<IP-DO-ESP32>` |
| Porta | 4048 |
| WLED Color Order | RGB (a ordem real GRB fica no WLED) |
| WLED RGBW | desligado |
| WLED brightness | 255 (cores enviadas sem mudança) |
| Also drive Home Assistant lights | desligado |

## Layout dos LEDs (LED Layout)

| Opção | Valor |
|---|---|
| Esquerda / Topo / Direita / Embaixo | 39 / 71 / 39 / 71 (total 220) |
| Lados ativos | os quatro em On |
| Bottom gap (soundbar) | 0 |
| Margens de captura (esq., topo, dir., baixo) | 0 / 0 / 0 / 0 % |
| LED offset | 0 |
| Scan Depth | 10 % |
| LED Start Corner | Bottom left |
| LED Direction | Clockwise |

## Captura

| Opção | Valor |
|---|---|
| Capture Source | Screen |
| Capture Method | MediaProjection (Standard) |
| Capture Rate | 30 fps |
| Capture Quality | High (256px) |
| Send Average Screen Color | desligado |
| Update Frequency | 60 Hz |
| Lighting delay | padrão (sem ajuste por app) |

## Cores (Color Processing ligado)

| Opção | Valor |
|---|---|
| Brightness | 100 % |
| Contrast | 120 % |
| Black Level | 10 % |
| White Level | 100 % |
| Saturation | 160 % |
| Brilho R / G / B | 100 / 100 / 100 % |
| Gama R / G / B | 100 / 100 / 100 % (a gama fica no WLED: 2.2) |

## Barras pretas e suavização

| Opção | Valor |
|---|---|
| Auto-detect letterbox | ligado |
| Black threshold | 18 RGB |
| Detection interval | 60 frames |
| Enable Smoothing | ligado |
| Smoothing Preset | Responsive |
| Settling Time | 50 ms |
| Output Delay | 0 ms |

## Geral

| Opção | Valor | Por quê |
|---|---|---|
| Grab on Boot | ligado | a captura volta sozinha quando a TV liga ou acorda |
| Keep running in standby | desligado | com ele ligado, os LEDs ficavam acesos com a TV em standby |
| Autostart permissions | não concedido | a captura voltou sozinha ao acordar mesmo assim |
| Language | Default | |

## Valores de cor: histórico

- Fita de teste de 12 V (GS1903, 24 pixels): saturação 200 %, contraste 130 %, preto 10 %, gama 150 %,
  gama 3.0 no WLED. Compensava o vermelho fraco da fita.
- Fita definitiva WS2812B pelo USB (limite de 500 a 850 mA): valores acima. Recalibrar quando a fonte de 5 V 10 A entrar.

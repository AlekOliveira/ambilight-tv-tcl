# Pendências do ambilight

Correções e melhorias para fazer depois.

## Rede
- [ ] Reservar IP fixo para o ESP32 no roteador (MAC e IPs reais em `local/rede.md`, fora do Git). Já mudou duas vezes, uma a cada reinício do roteador. Sem reserva, o UAL pode acabar mandando dados para outro aparelho. Depois disso, conferir o host no UAL.
  - O roteador é da Claro, com firmware limitado. A reserva de DHCP pode não existir ou não funcionar direito.
  - Plano B, se não der no roteador: IP fixo no próprio WLED (Config > WiFi Setup > Static IP), escolhendo um endereço fora da faixa do DHCP da Claro para não colidir com outro aparelho.
  - Plano C: usar um roteador próprio atrás do da Claro.

## Fita definitiva (5 V WS2812B, chegou 2026-11-07)
- Testada 2026-11-07: 300 LEDs acendem, ordem GRB confirmada (vermelho, verde, azul certos). Teste feito com o ESP32 no USB do PC, fita alimentada pelo VIN, WLED com 300 LEDs e limitador em 500 mA. Backup da config anterior em `backups/wled_cfg_fita_teste_2026-11-07.json`.
- Chicote: conector JST da fita → preto = GND, branco = dados (GPIO16/RX2), vermelho = 5 V.
- [ ] Soldar: dados no GPIO16 (pino `RX2`), com resistor de 330 Ω; GND comum; capacitor de 1000 µF na entrada da fita; injeção de energia.
- [x] WLED: WS2812B, GRB, 220 LEDs (feito 2026-11-07).
- [ ] WLED: religar o limitador de corrente em cerca de 8500 mA (fonte de 5 V 10 A). Ele foi desligado para a fita de teste de 12 V.
- [x] UAL: 39 / 71 / 39 / 71, começa embaixo à esquerda subindo; teste de layout confirmado; Capture Quality High (256px) (feito 2026-11-07).
- Fita colada e soldada na TV (2026-11-07), alimentada provisoriamente pelo USB da TV via VIN, limitador em 500 mA (~3% do brilho) até a fonte chegar.
- [ ] Calibrar o canto inicial e o sentido com `tools/edge_compare.py`.

## Cores
- [ ] Refazer a calibração com a fita nova, usando a playlist "Solid Colors" (Color Screen Tests) no SmartTube: laranja, rosa e violeta.
- Fita de teste (2026-11-05): gama do WLED em 3.0 (correção de gama ligada para o tempo real). O laranja fica certo com gama alta, mas o violeta puxa para azul. O vermelho da fita é fraco em relação ao verde e ao azul.
- UAL tem ajustes de cor escondidos: ligar a chave **Color Processing** (Settings > Capturing). Aparecem brilho, contraste, níveis de preto e de branco, **saturação**, **brilho por canal R/G/B** e **gama por canal**, todos de 0 a 200%, com uma prévia.
- Fita de teste (2026-11-06): contraste 130%, nível de preto 10%, saturação 200%, brilho R/G/B 100%, gama R/G/B 150%. Com brilho por canal acima de 100% as cores ficavam lavadas (claros estouram para branco). Detecção de barras pretas ligada.
- Fita nova no USB (2026-11-07): WLED gama 2.8; UAL brilho 100%, contraste 120%, preto 10%, saturação 160%, R/G/B 100%, gama por canal 100%, smoothing Responsive (50 ms), Capture Quality High. Recalibrar quando a fonte chegar.
- [ ] Recalibrar esses valores com a fita nova. HyperHDR só se o UAL não der conta.

## Testes
- [ ] Comparar o atraso pelo Wi-Fi com o do USB (Adalight a 921600 baud).

## Fita de teste atual (provisória)
- 12 V, chip GS1903 (compatível com WS2811), 24 pixels (3 LEDs por chip), ordem BRG.
- UAL em 4 / 8 / 4 / 8. Começa embaixo à esquerda e sobe.
- UAL Scan Depth em 10% (era 1%, que perdia cores perto da borda). Reavaliar com a fita nova.

## Animação ao ligar a TV
- Presets no WLED (arquivo em `wled/presets.json`, backup anterior em `backups/`): 1 = cometa azul (Meteor) com `lor:2`, 2 = apagado com `lor:0`, 3 = sequência (cometa 5 s, depois apagado).
- Para disparar: `POST /json/state` com `{"lor":2,"ps":3}`. O `lor:2` faz o WLED ignorar o UAL durante o cometa; o preset 2 devolve o controle.
- Preset de boot ficou no 2 (apagado). Motivo: no standby a TV liga e desliga o USB várias vezes, e o ESP32 reinicia a cada vez; com o cometa no boot ele piscaria com a TV desligada. Com a fonte definitiva o ESP32 fica sempre ligado, então o boot também não serviria de gatilho.
- UAL (2026-11-07): "Keep running in standby" desligado (antes os LEDs ficavam acesos com a TV em standby) e "Grab on Boot" ligado (captura volta sozinha ao acordar; testado).
- [ ] Gatilho ao ligar a TV: app de automação na TV (ex.: MacroDroid) com gatilho "tela ligada" mandando o comando acima, com atraso de ~5 s enquanto o ESP32 conecta no Wi-Fi. Precisa da autorização do usuário para instalar.
- "Autostart permissions" do UAL está "Not granted" (concede por ADB). Não mexi; até agora a captura voltou sozinha ao acordar.
- [x] Gatilho ao ligar a TV feito no Free My TV (2026-11-07): `RemoteKeyService` escuta "tela ligada" e manda `{"lor":2,"ps":3}` para o WLED. Endereço no arquivo da TV `Android/data/io.freemytv/files/ambilight.txt` (linha 1 a URL, linha 2 o JSON). Testado duas vezes: cometa ~6 s e depois o UAL assume.
- [ ] Se o IP do ESP32 mudar, atualizar esse arquivo na TV (`adb push`) e o host no UAL.
- Abertura trocada para Preenchimento (preset 12, Wipe azul, ~4 s) em 2026-11-07. Opções de teste guardadas nos presets 11 a 17.
- [x] Encerramento (presets 20, 23, 21, playlist 22): moldura laranja que recolhe LED por LED (efeito Percent, sem suavização), ~1 s. Free My TV manda a linha 3 do `ambilight.txt` (`{"lor":1,"ps":22}`) quando a tela desliga. Testado.
- [ ] Com a fonte, deixar o recolher mais lento (preset 23 `sx` menor e preset 22 `dur` maior): hoje é rápido porque a TV corta o USB ~1,5 s depois de desligar.
- Abertura agora (2026-11-07): laranja `[255,130,0]` enchendo LED por LED a partir do canto de baixo à esquerda (preset 12, efeito Percent, ~1,7 s) e segurando até ~3,5 s; depois entra o vídeo.

## Alexa
- WLED com integração Alexa ligada (2026-11-07): aparece como lâmpada Hue "Luz da TV" (emulação Espalexa, achada pelo Echo Dot 5 na rede). Comandos: ligar, desligar, brilho.
- A Alexa guarda o IP do ESP32: se o IP mudar, ela perde a lâmpada. Mais um motivo para o IP fixo (seção Rede).
- [ ] Se quiser comandos de efeito por voz: expor presets como lâmpadas extras (WLED Config > Sync > Alexa, "presets").
- ESP32 no carregador de celular (2026-11-07): fica sempre ligado. TV ligada = UAL comanda; TV desligada = Alexa/app WLED. Limitador em 850 mA (limite da placa pelo USB).
- Encerramento termina desligado (preset 21, `lor:0`) com cor de luminária guardada: branco quente `[255,150,60]`. "Alexa, liga a Luz da TV" acende nela. Boot do ESP32 também cai nesse preset.

# Astro Tracker para Home Assistant

Integração personalizada que usa a latitude e longitude de uma entidade `device_tracker` para calcular e consultar fenómenos relacionados com o Sol, Lua, eclipses, planetas, estações, meteoros e meteorologia espacial.

## Funcionalidades

- Segue dinamicamente a localização do `device_tracker`.
- Recalcula automaticamente quando a posição muda mais do que a distância configurada.
- Sol: elevação, azimute, nascer, pôr, dia/noite e fase de luz.
- Lua: fase, iluminação, idade, distância, elevação, azimute, nascer e pôr.
- Planetas: posição atual de Mercúrio, Vénus, Marte, Júpiter e Saturno.
- Eclipses lunares calculados localmente, incluindo indicação de Lua acima/abaixo do horizonte.
- Eclipses solares globais obtidos do U.S. Naval Observatory.
- Equinócios e solstícios adaptados ao hemisfério atual.
- Chuvas de meteoros principais com picos anuais aproximados.
- Índice Kp e alertas de meteorologia espacial NOAA/SWPC.
- Nebulosidade, visibilidade e precipitação Open-Meteo.
- Índice prático de qualidade de observação de 0 a 100%.
- Calendário `calendar.fenomenos_astronomicos` para automações e dashboards.
- Botão para atualização manual.

## Instalação pelo HACS

1. No Home Assistant, abrir **HACS → Integrações**.
2. Abrir o menu **⋮ → Repositórios personalizados**.
3. Adicionar `https://github.com/BrunoCunha1983-creator/astro_tracker` como categoria **Integration**.
4. Procurar **Astro Tracker** e selecionar **Download**.
5. Reiniciar o Home Assistant.
6. Abrir **Definições → Dispositivos e serviços → Adicionar integração**.
7. Procurar **Astro Tracker** e selecionar o `device_tracker`.

Depois de instalado pelo HACS, futuras versões podem ser atualizadas através do próprio HACS.

## Instalação manual

1. Descompactar o ZIP.
2. Copiar a pasta `custom_components/astro_tracker` para `/config/custom_components/astro_tracker`.
3. Reiniciar o Home Assistant.
4. Abrir **Definições → Dispositivos e serviços → Adicionar integração**.
5. Procurar **Astro Tracker**.
6. Selecionar o `device_tracker` com latitude e longitude.

## Fontes e funcionamento sem Internet

Os cálculos astronómicos principais são feitos localmente com Skyfield e efemérides JPL incluídas pelo pacote `skyfield-data`. Sem Internet continuam disponíveis Sol, Lua, planetas, fases, estações e eclipses lunares. As condições meteorológicas, Kp/alertas e catálogo online de eclipses solares ficam temporariamente indisponíveis até regressar a ligação.

## Limitação da versão 0.1.0

O catálogo USNO fornece a data global dos eclipses solares futuros, mas esta versão ainda não calcula a faixa geográfica exata nem a percentagem local de ocultação para eclipses solares. Os eclipses lunares já incluem visibilidade aproximada na posição do tracker.

# Astro Tracker para Home Assistant

Integração personalizada que usa a latitude e longitude de uma entidade `device_tracker` para calcular e consultar fenómenos relacionados com o Sol, Lua, eclipses, planetas, estações, meteoros e meteorologia espacial.

## Funcionalidades

- Segue dinamicamente a localização do `device_tracker`.
- Recalcula automaticamente quando a posição muda mais do que a distância configurada.
- Sol: elevação, azimute, nascer, pôr, dia/noite e fase de luz.
- Lua: fase, iluminação, idade, distância, elevação, azimute, nascer e pôr.
- Planetas: posição atual de Mercúrio, Vénus, Marte, Júpiter e Saturno.
- Eclipses lunares calculados localmente, incluindo indicação de Lua acima/abaixo do horizonte.
- **Eclipses solares calculados localmente e em tempo real com Skyfield/JPL.**
- **Percentagem de ocultação do Sol em tempo real.**
- **Magnitude, separação Sol-Lua, fase parcial/total/anular e visibilidade local.**
- **Contactos locais, máximo local e contagem decrescente até ao máximo.**
- Catálogo global de eclipses solares futuros obtido gratuitamente do U.S. Naval Observatory quando existe Internet.
- Equinócios e solstícios adaptados ao hemisfério atual.
- Chuvas de meteoros principais com picos anuais aproximados.
- Índice Kp e alertas de meteorologia espacial NOAA/SWPC.
- Nebulosidade, visibilidade e precipitação Open-Meteo.
- Índice prático de qualidade de observação de 0 a 100%.
- Calendário `calendar.fenomenos_astronomicos` para automações e dashboards.
- Botão para atualização manual.

## Eclipse solar em tempo real — versão 0.2.0

O eclipse solar local não depende de uma API paga. A integração usa as efemérides JPL fornecidas por `skyfield-data` e calcula diretamente no Home Assistant a posição topocêntrica aparente do Sol e da Lua para a latitude/longitude atual do `device_tracker`.

O ciclo de atualização é adaptativo e não faz pedidos à Internet:

- Durante um eclipse geométrico ativo: **1 segundo**.
- Quando Sol e Lua já estão próximos de um eclipse: **5 segundos**.
- Fora de um eclipse: verificação local a cada **10 segundos**.

As atualizações rápidas do eclipse usam apenas cálculo local. O intervalo normal do coordinator continua reservado para meteorologia, NOAA e outras fontes online.

### Entidades do eclipse solar

A versão 0.2.0 acrescenta, entre outras:

- `sensor.astro_tracker_solar_eclipse_phase`
- `sensor.astro_tracker_solar_eclipse_obscuration`
- `sensor.astro_tracker_solar_eclipse_magnitude`
- `sensor.astro_tracker_solar_eclipse_separation`
- `sensor.astro_tracker_solar_eclipse_max_obscuration`
- `sensor.astro_tracker_solar_eclipse_progress`
- `sensor.astro_tracker_solar_eclipse_seconds_to_maximum`
- `sensor.astro_tracker_solar_eclipse_start`
- `sensor.astro_tracker_solar_eclipse_maximum`
- `sensor.astro_tracker_solar_eclipse_end`
- `sensor.astro_tracker_solar_eclipse_updated_at`
- `binary_sensor.astro_tracker_solar_eclipse_active`
- `binary_sensor.astro_tracker_solar_eclipse_visible`
- `binary_sensor.astro_tracker_solar_eclipse_totality`
- `binary_sensor.astro_tracker_solar_eclipse_annularity`

> Se uma instalação já tiver entidades com nomes personalizados, o Home Assistant preserva esses IDs. Nesse caso basta selecionar as entidades equivalentes no card.

## Card Lovelace incluído

Está incluído no repositório:

`lovelace/solar_eclipse_card.yaml`

O card usa **apenas cartões nativos do Home Assistant**. Não necessita Mushroom, card-mod ou qualquer frontend adicional.

Para usar:

1. Abrir o dashboard do Home Assistant.
2. **Editar dashboard → Adicionar cartão → Manual**.
3. Copiar o conteúdo de `lovelace/solar_eclipse_card.yaml`.
4. Guardar.

O card apresenta:

- percentagem de ocultação num gauge 0–100%;
- fase atual do eclipse;
- magnitude;
- tempo até ao máximo;
- ocultação máxima local;
- progresso do eclipse;
- início, máximo e fim locais;
- separação Sol-Lua;
- eclipse visível/ativo;
- totalidade ou anularidade;
- instante da última atualização;
- aviso destacado quando entra em totalidade.

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

## Funcionamento gratuito e sem Internet

Os cálculos astronómicos principais são feitos localmente com Skyfield e efemérides JPL incluídas pelo pacote `skyfield-data`.

Sem Internet continuam disponíveis:

- posição do Sol e da Lua;
- fases da Lua;
- planetas;
- estações;
- eclipses lunares;
- **eclipse solar local em tempo real**;
- **ocultação, magnitude e contactos do eclipse solar**.

Quando não existe Internet ficam temporariamente indisponíveis apenas as funcionalidades que usam fontes online, como meteorologia Open-Meteo, NOAA/SWPC e o catálogo global USNO.

## Recorder e atualizações de 1 segundo

Durante um eclipse ativo algumas entidades mudam a cada segundo. Isto é intencional para permitir um card realmente em tempo real. Se não quiser guardar milhares de estados no histórico, pode excluir do Recorder as entidades mais rápidas, por exemplo:

```yaml
recorder:
  exclude:
    entities:
      - sensor.astro_tracker_solar_eclipse_separation
      - sensor.astro_tracker_solar_eclipse_seconds_to_maximum
      - sensor.astro_tracker_solar_eclipse_updated_at
```

A exclusão do Recorder não impede que os valores continuem a atualizar no dashboard.

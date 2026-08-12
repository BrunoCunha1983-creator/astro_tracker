# Astro Tracker

Integração HACS para Home Assistant que segue a localização de um `device_tracker` e disponibiliza fenómenos astronómicos locais: Sol, Lua, planetas, eclipses, estações, chuvas de meteoros, meteorologia espacial e condições de observação.

## Versão 0.2.0

Inclui agora **eclipse solar local em tempo real**, calculado gratuitamente no próprio Home Assistant com Skyfield/JPL:

- ocultação do Sol em percentagem;
- magnitude;
- fase parcial, total ou anular;
- contactos e máximo locais;
- contagem até ao máximo;
- separação Sol-Lua;
- visibilidade segundo a localização do `device_tracker`;
- atualização de 1 segundo durante o eclipse ativo;
- card Lovelace nativo em `lovelace/solar_eclipse_card.yaml`.

Não é necessária nenhuma API paga para os cálculos do eclipse solar.

## Instalação

Adicione este repositório ao HACS como **Integration**, instale **Astro Tracker**, reinicie o Home Assistant e configure a integração em **Definições → Dispositivos e serviços**.

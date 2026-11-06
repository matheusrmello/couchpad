# Reconstrução e validação — 06/11/2026

A beta 0.1.0b1 foi reempacotada em Debian 12 para reduzir o requisito do
AppImage de glibc 2.44 para **glibc 2.36**. O Flatpak local contém o mesmo
payload nativo. A versão pública foi preservada; os hashes identificam esta rodada.

## Construção

- Debian 12, Python 3.11.2, GTK 3.24, cairo 1.16.0.
- PyInstaller 6.22.3, appimagetool 1.9.1 (SHA-256 verificado pelo build).
- Inclusão explícita dos clientes Wayland/XCB que PyInstaller omitia.
- Carregador SVG GdkPixbuf/librsvg dessa base, sem o auxiliar Glycin do build antigo.
- Configuração de fontes da base incluída; variáveis privadas são removidas
  ao chamar ferramentas do host.
- Verificação dos ELFs coletados recusa símbolos GLIBC acima de 2.36.

## Testes

| Verificação | Resultado |
|---|---|
| Suíte unittest | 56 testes aprovados |
| AppImage em Debian 12 limpo, glibc 2.36 | Versão e runtime passaram |
| AppImage em Debian 13 limpo, glibc 2.41 | Versão e runtime passaram |
| AppImage em Ubuntu 24.04 limpo, glibc 2.39 | Versão e runtime passaram |
| AppImage em Ubuntu 26.04 limpo, glibc 2.43 | Versão e runtime passaram |
| AppImage em Fedora 44 limpo, glibc 2.43 | Versão e runtime passaram |
| AppImage em Arch limpo, glibc 2.44 | Versão e runtime passaram |
| Inicialização do AppImage na sessão gráfica | Janela/processo mantido, monitor próprio respondendo, automação desligada |
| Encerramento do teste gráfico | SIGTERM ao grupo de processos; monitor/socket removidos, sem estado pendente |
| Flatpak instalado para o usuário | Versão, runtime e doctor passaram; TV, monitor e áudio detectados |

Os contêineres não receberam bibliotecas extras. `--runtime-check` carregou
GTK, cairo, evdev e os oito SVGs. Não houve teste de uma sessão gráfica
independente de cada distribuição. Imagens e digests constam no JSON de resultados.

## Validação física no equipamento atual

Teste com o AppImage, configuração e estado temporários, sem Steam/launchers
nem CEC, em modo **extend**:

- TV Samsung HDMI-A-3 ativada em 3840 × 2160, escala **2.75**.
- Monitor DP-2 permaneceu ativo em 1920 × 1080, escala 1.
- Áudio mudou para `alsa_output.pci-0000_04_00.0.hdmi-stereo-extra1`.
- Volume da saída ativa verificado em 65536 por canal, equivalente a 100%.
- A restauração foi executada em `finally`: topologia, modo, posição, escala,
  saída padrão, volumes disponíveis e perfis coincidiram com o estado anterior.
- A TV voltou a desativada com escala anterior 1.7; nenhum journal ficou pendente.
- O monitor isolado também identificou o 8BitDo, mas não foi repetido um
  acionamento físico por botão ou desligamento do controle nesta rodada.

A leitura de estado não confirma som audível nem avaliação visual do painel.
Permanecem avisos não fatais GTK (escala de widget), módulos GTK do tema do host
não incluídos e avisos de regras de fontes do host mais novo durante a abertura.
Não impediram os resultados descritos; a inclusão de configuração privada de
fontes não eliminou todos os avisos. Não foi feita validação de HDR ou CEC.

## Flatpak e alcance

ID `io.github.matheusrmello.CouchPad`, branch `beta`, runtime do lançador
`org.freedesktop.Platform//25.08`. O lançador localiza o payload por
`app-path` em `/.flatpak-info` e usa `flatpak-spawn --host`.

A permissão `org.freedesktop.Flatpak=talk` permite execução como o usuário no
host; este pacote **não isola o aplicativo no sandbox**. Isso mantém acesso a
KScreen, evdev, áudio e identidade dos processos. O host precisa de glibc 2.36,
KDE Plasma/Wayland, XWayland, kscreen-doctor, pactl e permissões de controle.
Preferências, estado e IPC permanecem nos caminhos nativos shiftpad-linux.

O Flatpak está instalado apenas para o usuário nesta máquina, não publicado
no Flathub. Não foi testado Flatpak em outras distribuições. Use o menu da
interface para encerrar; `flatpak kill` não controla o processo do host.
A referência oficial da permissão e de `flatpak-spawn` está no
[manual Flatpak](https://docs.flatpak.org/en/latest/flatpak-command-reference.html).

## Artefatos desta rodada

- AppImage: `46930424` bytes, SHA-256 `83a14f1e9f6ff9405a03a37c0549d657190624bdc32683cba216ef30063804ae`.
- Flatpak: `37757688` bytes, SHA-256 `31cdc9f608a5b1fb2128e023048f5daec82ab60225de3a43a018bd572d330ee5`.

Manifestos: `dist/build-info.json`, `dist/flatpak-build-info.json`.
Matriz: `dist/runtime-results.json`; hardware: `dist/hardware-results.json`.
Logs locais: `.build/runtime-qa/` e `.build/packaged-session.log`.
Essas saídas são ignoradas pelo Git; este relatório é o registro versionável.

## Reprodução

```bash
python3 tools/build_portable.py
python3 tools/test_portable_runtime.py
python3 tools/test_packaged_session.py
python3 tools/build_flatpak.py
flatpak install --user dist/CouchPad-0.1.0b1-x86_64.flatpak
flatpak run io.github.matheusrmello.CouchPad --runtime-check
flatpak run io.github.matheusrmello.CouchPad doctor
```

A inspeção dos símbolos do payload não é uma prova de todos os requisitos de
kernel/CPU/driver. O runtime AppImage baixado por appimagetool continua vindo
da release corrente; o build não é bit a bit reproduzível. Os pacotes Debian
também podem receber atualizações. O manifesto e os testes do artefato efetivo
continuam necessários para cada reconstrução.

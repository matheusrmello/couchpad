# CouchPad — Flatpak de integração com o desktop

ID: `io.github.matheusrmello.CouchPad`, branch `beta`, x86_64.

Este pacote instala o executável autocontido construído em Debian 12. O
lançador roda no runtime `org.freedesktop.Platform//25.08` e executa o payload
no host com `flatpak-spawn --host`. A permissão
`--talk-name=org.freedesktop.Flatpak` permite executar programas como o usuário:
**o aplicativo não fica isolado pelo sandbox do Flatpak**. Isso preserva o
acesso a KScreen, áudio, evdev, processos e restauração do desktop.

Requisitos do host: Linux x86_64, glibc >= 2.36, KDE Plasma/Wayland, XWayland,
`kscreen-doctor`, `pactl`, sessão D-Bus e acesso aos controles em `/dev/input`.
Não é um adaptador para GNOME/Windows nem um pacote aprovado pelo Flathub.
O runtime Flatpak não substitui a glibc do host neste modo de execução.

## Construir e instalar

```bash
python3 tools/build_portable.py
python3 tools/build_flatpak.py
flatpak install --user dist/CouchPad-0.1.0b1-x86_64.flatpak
flatpak run io.github.matheusrmello.CouchPad --version
flatpak run io.github.matheusrmello.CouchPad --runtime-check
flatpak run io.github.matheusrmello.CouchPad doctor
flatpak run io.github.matheusrmello.CouchPad
```

O build usa as ferramentas `flatpak build-finish/export/bundle`; não requer
`flatpak-builder` nem SDK, pois o payload já foi compilado no contêiner.
O runtime pode ser instalado pelo Flatpak a partir do Flathub durante a instalação.
O bundle local não é assinado; acompanham SHA-256 e manifesto em `dist/`.

Preferências, estado, lock e socket são os mesmos da instalação nativa em
`shiftpad-linux`; não são migrados para `~/.var/app`. Use **Encerrar CouchPad**
na interface para aguardar a restauração. `flatpak kill` não supervisiona o
processo executado no host. Desinstalar o Flatpak mantém as preferências nativas.
Não desinstale/atualize o pacote durante uma sessão ativa: encerre-o primeiro.

# CouchPad — AppImage com base Debian 12

Reconstrução de 06/11/2026, versão 0.1.0b1, Linux x86_64.

## Construir

Requer Podman rootless configurado e acesso à rede para baixar Debian 12,
seus pacotes, PyInstaller 6.22.3 e appimagetool 1.9.1. Não instala pacotes no host.

```bash
python3 tools/build_portable.py
python3 tools/test_portable_runtime.py
python3 tools/test_packaged_session.py
```

O contêiner instala Python 3.11, PySide6/Qt Quick, GTK 3 e dependências Debian 12 (glibc 2.36).
O PyInstaller coleta o runtime, SVGs, bibliotecas e configuração de fontes.
São incluídos explicitamente os clientes Wayland/XCB omitidos pela coleta padrão.
Essa base usa o carregador GdkPixbuf/librsvg, sem depender do subprocesso Glycin
que falhava no pacote anterior. `COUCHPAD_MAX_GLIBC` tem padrão 2.36 e o build
recusa ELFs coletados acima desse limite, antes de produzir o AppImage.

Saídas em `dist/`: AppImage, `.sha256`, `build-info.json` e, após os testes,
`runtime-results.json`. O manifesto contém Python, glibc, SHA-256 do pacote e
da ferramenta. O build não é bit a bit reproduzível: os pacotes Debian podem
receber atualizações e appimagetool busca o runtime AppImage corrente.

## Executar

```bash
./dist/CouchPad-0.1.0b1-x86_64.AppImage --version
./dist/CouchPad-0.1.0b1-x86_64.AppImage --runtime-check
./dist/CouchPad-0.1.0b1-x86_64.AppImage doctor
./dist/CouchPad-0.1.0b1-x86_64.AppImage
```

Sem FUSE, acrescente `--appimage-extract-and-run` antes dos argumentos.
Use Encerrar CouchPad na interface para aguardar o encerramento do monitor
próprio e a restauração; não mate apenas o processo pai do modo de extração.

Requisitos do host: glibc >= 2.36, KDE Plasma/Wayland, XWayland,
`kscreen-doctor`, `pactl`, sessão D-Bus e leitura de `/dev/input`.
Notificações usam `notify-send`/`gdbus`; abertura de arquivos usa `xdg-open`/`gio`.
Steam/Hydra são externos. Primeiro uso cria configuração desativada, sem launcher.
Não instala atalhos nem serviços automaticamente.

Os testes limpos de Debian 12/13, Ubuntu 24.04/26.04, Fedora 44 e Arch passaram
em versão e runtime, sem instalar bibliotecas extras nas imagens de teste.
Não certificam automação de hardware nesses sistemas nem outro desktop.

O pacote antigo exigia glibc 2.44; seu histórico está preservado em
[teste Distrobox](../../docs/testes-distrobox.md). O mesmo número 0.1.0b1 foi
mantido; diferencie os artefatos pelo manifesto e SHA-256.

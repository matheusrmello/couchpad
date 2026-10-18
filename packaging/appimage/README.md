# CouchPad 0.1.0b1 — AppImage beta local

Esta beta mantém GTK3 e foi construída para teste local em Linux x86_64.
Inclui Python, GTK, PyGObject, cairo, evdev e os ícones do aplicativo.
Não depende da pasta do projeto nem de Python instalado para executar.
Os testes posteriores identificaram uma dependência externa do subprocesso de
imagens: o Arch limpo precisou de `librsvg` e `fontconfig` para o runtime passar.
Consulte o [relatório de Distrobox](../../docs/testes-distrobox.md) e a
[documentação de build/testes](../../docs/build-testes.md).

## Executar

Torne `CouchPad-0.1.0b1-x86_64.AppImage` executável e abra com dois cliques,
ou execute pelo terminal. Sem argumentos, abre a interface e inicia o monitor
automático quando necessário. Se já existir um monitor da instalação atual,
reutiliza esse processo e não o encerra ao sair.

Na primeira execução sem configuração, detecta os monitores e cria um perfil
**desativado**, sem inicializador configurado. Selecione os dispositivos e
ative o CouchPad pela janela. As preferências existentes são preservadas.

Fechar a janela mantém o aplicativo na bandeja. Quando o AppImage iniciou seu
próprio monitor, **Encerrar CouchPad** encerra também esse processo e restaura
o desktop antes de sair. Quando reutiliza um serviço existente, o menu mostra
**Fechar interface** e o serviço continua funcionando.

```bash
./CouchPad-0.1.0b1-x86_64.AppImage --version
./CouchPad-0.1.0b1-x86_64.AppImage --runtime-check
./CouchPad-0.1.0b1-x86_64.AppImage doctor
./CouchPad-0.1.0b1-x86_64.AppImage status
```

Se FUSE não estiver disponível, use `--appimage-extract-and-run` antes dos
argumentos. O aplicativo não instala serviços nem atalhos automaticamente.

## Requisitos e alcance desta beta

- KDE Plasma com Wayland, XWayland e `kscreen-doctor` do sistema.
- PipeWire com compatibilidade PulseAudio ou PulseAudio, com `pactl` no sistema.
- Sessão D-Bus; `notify-send` e `gdbus` para notificações; `xdg-open`/`gio` para
  abrir arquivos ou atalhos. Steam/Hydra continuam sendo aplicativos externos.
- Permissão de leitura dos dispositivos de controle em `/dev/input`.
- A versão mínima observada é glibc **2.44**; consulte o manifesto externo
  `dist/build-info.json` correspondente ao artefato em uso. A compilação local
  usa bibliotecas do CachyOS. Debian 13, Ubuntu 26.04 e Fedora 44 foram testados
  em contêiner e falharam por ausência dos símbolos GLIBC_2.44 exigidos.
- Outros ambientes gráficos ainda precisam de adaptadores de controle de telas.

Configuração: `$XDG_CONFIG_HOME/shiftpad-linux/config.toml` (normalmente
`~/.config/shiftpad-linux/config.toml`). Estado de restauração:
`$XDG_STATE_HOME/shiftpad-linux/session.json`. Os nomes históricos são mantidos
para preservar as preferências e impedir duas automações concorrentes.

## Construir novamente

No sistema de build, instale GTK3/PyGObject, pycairo, evdev, seus typelibs,
`mksquashfs`, `curl` e Python. Depois, na raiz do projeto:

```bash
python3 -m venv --system-site-packages .build/venv
.build/venv/bin/python -m pip install 'pyinstaller==6.22.3'
mkdir -p .build/downloads
curl -fL https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -o .build/downloads/appimagetool-x86_64.AppImage
chmod +x .build/downloads/appimagetool-x86_64.AppImage
.build/venv/bin/python tools/build_appimage.py
```

O resultado, o SHA-256 e os dados do build ficam em `dist/`. Para distribuição
ampla, reconstruir em uma base mais antiga, corrigir o acesso do carregador SVG
às suas dependências e validar a matriz de sistemas. Regerar documentação no
projeto não atualiza o texto interno de um AppImage já construído.

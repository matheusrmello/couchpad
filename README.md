# CouchPad

Aplicativo para preparar uma sessão de jogo na TV ao acionar um controle e
restaurar o desktop depois. Implementação independente em **Python e GTK 3**,
inspirada no fluxo do ShiftPad para Windows.

**Versão atual: 0.1.0b1 — beta local para KDE Plasma/Wayland.**
A interface usa XWayland. Outros ambientes gráficos e Windows fazem parte dos
planos futuros; não há suporte universal implementado.

## Documentação do projeto

[**Abrir o índice completo**](docs/README.md)

| Guia | Conteúdo |
|---|---|
| [Funcionalidades](docs/funcionalidades.md) | Uso da janela, controles, TV, áudio, Steam/Hydra, autosave e limitações |
| [Arquitetura técnica](docs/arquitetura.md) | Módulos, estados, processos, IPC, persistência e recuperação |
| [Configuração e operação](docs/configuracao-operacao.md) | TOML, comandos, primeiro uso, serviços e diagnóstico |
| [Histórico e decisões](docs/historico-decisoes.md) | Origem, referências, identidade visual, pedidos e correções |
| [Build e testes](docs/build-testes.md) | AppImage, dependências, resultados reais e matriz de compatibilidade |
| [Planos futuros](docs/planos-futuros.md) | Portabilidade Linux, adaptadores por DE, melhorias e Windows |
| [Relatório funcional](docs/verificacao-2026-10-17.md) | Rodada histórica de verificações GTK, serviço e hardware |
| [Relatório Distrobox](docs/testes-distrobox.md) | Resultados concretos de Arch, Debian, Ubuntu e Fedora |

## Funcionalidades implementadas

- Ativação/desativação persistente, permitindo jogar com o controle no monitor.
- Descoberta e seleção de TV, controle e saída de áudio, com identificação EDID
  e IDs do controle quando disponíveis.
- TV exclusiva, desktop estendido ou espelhamento; recuperação da configuração
  anterior e tentativa de restauração após interrupção.
- Saída de áudio da TV em **100%**, preservando volumes/perfis anteriores.
- Escala **275% em resolução 4K**; Full HD mantém a escala, sem alterar a resolução.
- Steam Big Picture e outro inicializador, com argumentos e fechamento opcional
  somente do processo próprio do inicializador.
- Contagem regressiva, cancelamento, atrasos, bandeja e autosave.

O gravador visual de combinação ainda não existe: **Editar combinação** abre o
TOML. HDR/CEC têm caminhos de código/configuração, mas faltam ensaios físicos.
Receptores que permanecem expostos após desligar o controle, como o GameSir
observado, podem exigir restauração manual.

## AppImage e Flatpak — reconstrução de 06/11/2026

O AppImage foi reconstruído em **Debian 12, Python 3.11 e glibc 2.36**, substituindo
no pacote atual a exigência anterior de glibc 2.44. O build verifica todos os
ELFs coletados e recusa símbolos acima de GLIBC_2.36. As bibliotecas de cliente
Wayland/XCB e o carregador SVG estão incluídos.

Artefatos locais:

- `dist/CouchPad-0.1.0b1-x86_64.AppImage`
- `dist/CouchPad-0.1.0b1-x86_64.flatpak`

Ambos continuam requerendo **Linux x86_64, KDE Plasma/Wayland, XWayland,
kscreen-doctor, pactl e permissão de leitura dos controles**. glibc 2.36 é o piso
do novo payload; não significa suporte a qualquer desktop.

O mesmo AppImage passou em `--version` e `--runtime-check` (GTK, cairo, evdev e
8 SVGs) em contêineres limpos de Debian 12/13, Ubuntu 24.04/26.04, Fedora 44 e
Arch, sem instalar dependências extras. Isso valida carregamento, não a
integração física com todos esses sistemas.

O Flatpak é um **pacote de integração com o host**: usa
`flatpak-spawn --host` para executar seu payload, com acesso como o usuário.
Não oferece isolamento do backend e ainda exige glibc >= 2.36 no host.
Não foi publicado no Flathub. Veja [o manual Flatpak](packaging/flatpak/README.md).

```bash
python3 tools/build_portable.py
python3 tools/build_flatpak.py
flatpak install --user dist/CouchPad-0.1.0b1-x86_64.flatpak
flatpak run io.github.matheusrmello.CouchPad
```

Sem argumentos, os pacotes abrem a janela e iniciam/reutilizam o monitor.
Um perfil novo começa desativado; preferências existentes são preservadas.
`dist/` e `.build/` são ignorados pelo Git. A versão pública foi preservada;
identifique esta reconstrução pelos hashes e manifestos que acompanham o binário.

[Manual AppImage](packaging/appimage/README.md) ·
[Relatório desta reconstrução](docs/reconstrucao-2026-11-06.md).

## Executar e verificar pelo código

### Interface Qt/QML

A interface Qt Quick usa o mesmo monitor e socket, com seleção de TV, controle
 e áudio, modo de tela, atrasos, Steam e outro inicializador. As seleções de
 dispositivos e opções de sessão são salvas automaticamente; o outro programa
 possui botão de salvar. Há interface GTK histórica pelo comando `tray`.

Para executar do código, prepare a configuração e inicie o monitor:

```bash
python3 -m venv --system-site-packages .build/qt-venv
.build/qt-venv/bin/pip install -e '.[qt]'
.build/qt-venv/bin/python -m shiftpad_linux run
# Em outro terminal:
.build/qt-venv/bin/python -m shiftpad_linux qt
```

Os pacotes reconstruídos usam a interface Qt, com renderização por software
por padrão para compatibilidade gráfica. O suporte de sistema continua limitado
ao backend KDE/Wayland; Qt não adiciona adaptadores para GNOME ou Windows.

Requer Python 3.11+, evdev, GTK 3/PyGObject/cairo e as ferramentas de integração.
Prepare uma configuração própria antes de iniciar a interface ou a automação.
**`config.example.toml` contém os dispositivos do desenvolvimento**; ajuste os
nomes/identidades para sua máquina, inicialmente com `enabled = false`.

Consultas sem troca de tela:

```bash
python3 -m shiftpad_linux doctor
python3 -m shiftpad_linux devices
python3 -m shiftpad_linux preview
```

Com a configuração preparada, `run` inicia o monitor e `tray` abre a interface.
Os serviços opcionais em `systemd/` pressupõem a pasta da instalação de
desenvolvimento; não são necessários à supervisão própria do AppImage.
Veja [Configuração e operação](docs/configuracao-operacao.md) para os comandos
que alteram a sessão e os caminhos de recuperação.

A última execução registrada da suíte teve **56 testes aprovados**:

```bash
python3 -m unittest discover -s tests -v
```

Há ainda roteiros separados de integração GTK e de Distrobox, descritos em
[Build e testes](docs/build-testes.md). As evidências distinguem simulação,
verificação real local e confirmação visual do usuário.

## Identidade e origem

O nome público é **CouchPad**, com o SVG fornecido pelo usuário. O módulo
`shiftpad_linux`, os diretórios e os serviços históricos são mantidos para
preservar a instalação e as preferências existentes.

A análise anterior citada no projeto usou informações públicas do
[ShiftPad](https://github.com/APPLEVODKARUS/ShiftPad) e sua
[release 2.2.0](https://github.com/APPLEVODKARUS/ShiftPad/releases/tag/v2.2.0).
Não houve observação do programa Windows em execução que certifique paridade
completa. A implementação não executa o binário Windows nem inclui seu sistema
de trial/licenciamento. O histórico, a proveniência e as limitações da evidência
estão em [Histórico e decisões](docs/historico-decisoes.md).

## Licença

O código do CouchPad é distribuído sob a [licença MIT](LICENSE).
Bibliotecas e componentes incluídos no empacotamento mantêm suas próprias
licenças e avisos.

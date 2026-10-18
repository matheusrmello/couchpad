# Build, compatibilidade e testes

[Índice da documentação](README.md)

## Artefato atual

Versão do projeto: **0.1.0b1**. Nome do arquivo:
`dist/CouchPad-0.1.0b1-x86_64.AppImage`.

A beta foi construída no CachyOS x86_64 com glibc 2.44. O manifesto local registra
exigência de símbolos **GLIBC_2.44**. Isso foi confirmado por falhas concretas
nos contêineres com versões anteriores, não somente inferido do host de build.

O pacote tem aproximadamente 59,3 MiB. O tamanho exato e o checksum variam
conforme o build. Consulte o par `build-info.json`/`.sha256` produzido na mesma
rodada do binário; não use um hash antigo como identidade permanente da versão.

## Pipeline de empacotamento

1. Um venv de build usa os pacotes GTK/PyGObject do sistema via
   `--system-site-packages`; PyInstaller 6.22.3 foi instalado nesse ambiente.
2. `couchpad.spec` congela o entry point em modo **onedir**, coleta Python,
   módulos GI, evdev, cairo, typelibs, temas/ícones selecionados e assets próprios.
3. Em hosts GdkPixbuf/Glycin recentes, inclui auxiliares SVG/imagens, suas
   configurações e `bwrap` quando disponível.
4. O hook cria configuração Glycin temporária com caminhos relativos ao bundle
   efetivamente montado/extraído.
5. O roteiro monta `CouchPad.AppDir`: `AppRun`, desktop file, ícone e runtime
   em `usr/bin`, com documentos e avisos de dependências disponíveis no host.
6. `appimagetool` oficial gera o AppImage Type 2 usando SquashFS.
7. O roteiro calcula SHA-256, examina símbolos GLIBC dos ELFs com `readelf` e
   escreve `dist/build-info.json`.

A inclusão de avisos de bibliotecas é uma coleta dos diretórios disponíveis;
não é uma auditoria completa de redistribuição. O projeto usa a [licença MIT](../LICENSE),
recebida do repositório GitHub; os avisos e licenças das dependências e assets
deverão ser revisados antes da distribuição.

### Arquivos importantes

| Arquivo | Papel |
|---|---|
| `packaging/appimage/entry.py` | Encaminha para `portable.main()` |
| `packaging/appimage/couchpad.spec` | Coleta e congela aplicação/dependências |
| `packaging/appimage/runtime_hook.py` | Reloca carregadores de imagem |
| `packaging/appimage/AppRun` | Resolve AppDir e marca execução como AppImage |
| `packaging/appimage/couchpad.desktop` | Identidade no pacote |
| `tools/build_appimage.py` | Orquestra build, AppDir, empacotamento e manifesto |
| `packaging/appimage/README.md` | Instruções detalhadas e requisitos |

Os comandos de reconstrução estão no [manual do pacote](../packaging/appimage/README.md).
O roteiro exige host x86_64, PyInstaller e `appimagetool` previamente baixado.
Também usa ferramentas do host, incluindo `readelf` e o ambiente de SquashFS.
Os binários das ferramentas vêm de releases oficiais; o download `continuous`
não é uma fixação suficiente para um build bit a bit reproduzível.

`.build/` e `dist/` são ignorados. O build **não** inclui o TOML pessoal,
`session.json`, o diretório home do usuário ou os mocks de teste como dados do
produto. Seu pacote pode, porém, conter metadados técnicos de compilação.
Não se deve remover `.build/` ou volumes dos testes com contêineres ativos sem
primeiro encerrar os ambientes correspondentes.

## O que foi validado no AppImage

- `--version` retornou `0.1.0b1`.
- `--runtime-check` confirmou execução congelada, GTK 3.24, cairo, evdev e oito SVGs.
- Execução por FUSE e por `--appimage-extract-and-run`.
- `doctor` conseguiu consultar KScreen e PipeWire a partir do pacote.
- Abertura fora do diretório do projeto.
- Primeiro uso com diretórios XDG temporários: configuração desativada, TV e
  monitor detectados, sem copiar os IDs do exemplo de desenvolvimento.
- Início e encerramento de monitor próprio, sem depender das unidades systemd.
- Reuso do serviço existente sem criar um segundo monitor nem encerrá-lo ao sair.
- Preservação das preferências reais nos testes isolados.

O teste de runtime não aciona a TV e não equivale ao teste funcional completo.
Ao reutilizar um serviço já aberto, a interface congelada não comprova por si
só que aquele monitor também está executando dentro do AppImage. A rodada com
XDG/socket próprios foi usada para verificar a supervisão autônoma.

## Limitação confirmada de imagens/fontes

No Arch limpo, o comando de versão funcionou e o carregamento SVG falhou.
O auxiliar `glycin-svg` executado pelo sandbox não encontrou `librsvg-2.so.2`
e `libcairo.so.2` no userland do contêiner; também faltava a configuração de
fontconfig. As cópias no bundle não ficaram automaticamente disponíveis para
esse subprocesso isolado.

A instalação de `librsvg` e `fontconfig` **apenas no contêiner Arch** fez o
runtime-check passar. Isso revela uma dependência externa efetiva e precisa
ser corrigido no pacote. O resultado não autoriza anunciar um AppImage
completamente autossuficiente em qualquer instalação Arch.

Uma tentativa diagnóstica com variável de ambiente para o loader não eliminou
a falha; o pacote de distribuição não foi alterado para desativar o sandbox.
A solução deve preservar o isolamento adequado e tornar seus recursos e
bibliotecas disponíveis, ou usar uma base/runtime com carregamento compatível.

## Matriz observada

| Ambiente | glibc | Evidência |
|---|---|---|
| CachyOS de desenvolvimento, KDE/Wayland | 2.44 | Interface/AppImage e funções locais exercitadas; ver ressalvas de hardware |
| Arch Linux em Distrobox | 2.44 | Versão passa; runtime passa depois das dependências adicionais |
| Debian 13 em Distrobox | 2.41 | Binário falha por GLIBC_2.44 ausente |
| Ubuntu 26.04.1 em Distrobox | 2.43 | Binário falha por GLIBC_2.44 ausente |
| Fedora 44 em Distrobox | 2.43 | Binário falha por GLIBC_2.44 ausente |
| GNOME, outros compositores e X11 genérico | — | Sem adaptadores funcionais implementados |
| Windows, ARM64 e sistemas musl | — | Sem build/suporte validado |

Uma distribuição “base Arch” não é uma garantia de versão da glibc, CPU/ABI,
drivers ou integração. Mesmo com as bibliotecas certas, o backend atual ainda
exige KScreen e a sessão suportada. Reconstruir numa base mais antiga é uma
condição para ampliar o alcance, não uma certificação automática de todas as distros.

## Evolução das verificações

| Etapa | Evidência registrada |
|---|---|
| Antes das correções de integração | 35 testes automatizados aprovados |
| Perfil HDMI e comunicação da janela | 39 testes aprovados; 40 cenários GTK; 10 verificações reais da rodada |
| Volume/escala | 46 testes aprovados e uma ativação real na Samsung 4K |
| Iniciador AppImage | 56 testes aprovados, mais verificações manuais do pacote |

Os relatórios históricos não foram reescritos como se já contivessem recursos
adicionados depois. A contagem atual está dividida assim:

| Arquivo | Casos `test_*` |
|---|---:|
| `tests/test_audio_volume.py` | 3 |
| `tests/test_behavior.py` | 21 |
| `tests/test_control_and_settings.py` | 12 |
| `tests/test_discovery.py` | 8 |
| `tests/test_notifications.py` | 2 |
| `tests/test_portable.py` | 10 |
| **Total** | **56** |

Repetir a suíte, a partir da raiz:

```bash
python3 -m unittest discover -s tests -v
```

São testes Python do backend Linux. Não equivalem a uma execução em outro
sistema operacional. Há mocks de KScreen, áudio, notificações, controles,
processos e temporização conforme cada cenário.

### Roteiro GTK

```bash
python3 tools/qa_tray.py
```

Aciona sinais de widgets reais e verifica 40 cenários: botões, menus, modos,
autosave, escolha de dispositivos, argumentos, mensagens de falha e recuperação,
ocultação/reabertura e comportamento com serviço indisponível. Usa configuração
temporária, daemon simulado, escolha de arquivo simulada e editor simulado.
Consulta o hardware para compor a descoberta, sem aplicar mudanças de tela.

Não certifica visualmente todos os diálogos nativos, acessibilidade, foco,
posicionamento do Steam ou o menu acionado por mouse em cada DE.

### Hardware real e confirmações do usuário

Durante o desenvolvimento, o usuário confirmou troca para a TV, Steam Big
Picture visível, funcionamento dos botões de ativar/restaurar, bandeja/janela,
chave da automação, contagem e gravação visualmente confirmada de preferências.
Também houve confirmação de que desativar outro programa deixou abrir somente
Steam depois da correção.

A rodada registrada em [verificacao-2026-10-17.md](verificacao-2026-10-17.md)
verificou os três modos de vídeo, saída padrão e restauração, comandos Steam e
notificações. Os processos de teste usados para fechamento não eram jogos reais.
A inspeção de estado não comprova, sozinha, som audível nem renderização correta
do inicializador na TV.

A política nova de volume/escala teve uma validação real em `tv-only`: sink da
Samsung em 65536 por canal (100%), escala 2,75, restauração das escalas e dos
volumes disponíveis e preferências preservadas. Naquela execução o volume
anterior da TV já era 100%; a recuperação de valores menores e balanceamento
de canais diferentes foi coberta pelos testes automatizados.

Uma ativação física do 8BitDo passou de espera por botão para contagem e sessão
automática. Na última janela de observação o controle permaneceu conectado;
a restauração física por desligamento continua precisando de repetição
controlada. O receptor persistente do GameSir tem a limitação já documentada.
HDR, CEC, outra TV e várias combinações de hardware não foram certificados.

## Distrobox e DistroShelf

O [relatório completo](testes-distrobox.md) registra os quatro ambientes,
comandos, logs, glibc e falhas. Para repetir:

```bash
python3 tools/test_appimage_distrobox.py
python3 tools/test_appimage_distrobox.py arch
```

O roteiro usa Distrobox/Podman rootless, cria os contêineres dedicados se faltarem,
usa homes em `.build/distrobox/homes/` e monta `dist/` somente para leitura.
`--home` evita misturar preferências, mas **não impede o acesso ao home do host**;
não é uma garantia de isolamento de segurança. Os comandos executados limitam-se
a versão/runtime, sem ativar vídeo, áudio ou launcher.

Nomes: `couchpad-qa-arch`, `couchpad-qa-debian13`, `couchpad-qa-ubuntu2604` e
`couchpad-qa-fedora44`. Foram deixados parados depois da rodada. DistroShelf
pode gerenciar os mesmos contêineres por interface gráfica.

A imagem Arch usada agora já tem os pacotes adicionais; repetir o teste nela
não reproduz o resultado inicial “limpo”. Esse resultado foi salvo em
`.build/distrobox/arch-clean-results.json`. Não apagar contêineres de outras
tarefas para reconstruir a matriz.

Distrobox compartilha kernel e integração com a sessão do host. Uma janela GTK
aberta no contêiner continua podendo usar o compositor do CachyOS. Para validar
outro DE, usar sessão própria, compositor aninhado ou VM conforme o teste;
HDMI físico/áudio/controladores também exigem ensaio no hardware pertinente.

## Critérios para uma próxima beta distribuível

1. Construir numa base com glibc mais antiga e declarar o mínimo observado.
2. Corrigir a dependência externa do auxiliar SVG/fontconfig e repetir em
   userlands limpos, sem “consertar” cada contêiner antes do teste de baseline.
3. Verificar a interface completa, IPC, primeiro uso e restauração no pacote,
   não somente `--version`.
4. Publicar a matriz com versões de imagens e níveis de evidência.
5. Declarar arquiteturas e ambientes suportados; não equiparar interface GTK
   multiplataforma a backend de controle de telas multiplataforma.
6. Consolidar logs/testes reproduzíveis e revisar dependências, avisos/licença e
   metadados antes de publicação pública.

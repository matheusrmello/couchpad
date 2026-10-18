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

## AppImage beta local

Artefato gerado: `dist/CouchPad-0.1.0b1-x86_64.AppImage`.
Se estiver presente, já é executável; abra com dois cliques ou pelo terminal.
Sem argumentos, abre a janela e inicia/reutiliza o monitor automático.
Preferências existentes são preservadas; um perfil novo começa desativado.

O build local exige **x86_64 e glibc 2.44**, além de KDE Plasma/Wayland,
XWayland, `kscreen-doctor`, `pactl` e acesso aos dispositivos de controle.
Os testes identificaram dependências efetivas de SVG/fontconfig no subprocesso
de imagens, apesar de haver bibliotecas incluídas no pacote.

| Ambiente testado | Resultado deste pacote |
|---|---|
| CachyOS de desenvolvimento | Abertura e funcionamento local exercitados |
| Arch em Distrobox | Runtime passou após instalar `librsvg` e `fontconfig` no contêiner |
| Debian 13, Ubuntu 26.04 e Fedora 44 em Distrobox | Falha por ausência de GLIBC_2.44 |

Esses testes de contêiner não certificam a automação em outro DE. A próxima
etapa de distribuição é reconstruir numa base mais antiga e corrigir as
dependências do carregador de imagens.

[Manual do AppImage e reconstrução](packaging/appimage/README.md).
`dist/` e `.build/` são saídas locais ignoradas; a presença do binário não é
pressuposta num clone do projeto. Checksum e requisitos do artefato efetivo
constam em `dist/build-info.json` e no arquivo `.sha256` correspondente.

## Executar e verificar pelo código

Obtenha o projeto pelo repositório oficial:

```bash
git clone https://github.com/matheusrmello/couchpad.git
cd couchpad
```

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

# Documentação do CouchPad

Consolidação em **17/10/2026**, referente ao código **0.1.0b1**.

O CouchPad é uma implementação independente para levar uma sessão de jogo do
monitor à TV ao acionar um controle, ajustar áudio e inicializadores e restaurar
o desktop depois. O produto mantém **Python e GTK 3**. A beta atual integra-se
com **KDE Plasma em Wayland**, usando XWayland para a janela.

Esta documentação reúne o que foi implementado, as decisões da conversa,
os resultados disponíveis e as propostas futuras. **Planejamento não significa
suporte implementado; um teste de biblioteca não significa teste do desktop.**

## Como navegar

| Documento | Conteúdo |
|---|---|
| [Guia de uso e funcionalidades](funcionalidades.md) | Interface, automação, áudio, tela, controles, inicializadores e limites de cada recurso |
| [Arquitetura técnica](arquitetura.md) | Módulos, processos, estados, IPC, persistência, recuperação e dependências |
| [Configuração e operação](configuracao-operacao.md) | TOML, CLI, caminhos, serviços, primeiro uso e diagnóstico |
| [Histórico e decisões](historico-decisoes.md) | Origem, renomeações, evolução da interface, correções e escolhas do produto |
| [Build, compatibilidade e testes](build-testes.md) | AppImage, requisitos reais, evidências, matriz de distribuições e reprodução |
| [Planos futuros](planos-futuros.md) | Prioridades, adaptadores Linux, Windows, critérios de aceite e pendências |
| [Verificação funcional de 17/10](verificacao-2026-10-17.md) | Registro histórico da rodada com 39 testes unitários, 40 verificações GTK e 10 verificações reais |
| [Testes com Distrobox](testes-distrobox.md) | Resultados concretos de Arch, Debian, Ubuntu e Fedora |
| [Manual do empacotamento](../packaging/appimage/README.md) | Comandos para construir e executar a beta |

## Situação consolidada

| Área | Situação |
|---|---|
| Janela, bandeja, autosave e seleção de dispositivos | Implementados em GTK 3 |
| TV exclusiva, estender e espelhar | Implementados via KScreen; testados no equipamento de desenvolvimento |
| Áudio HDMI, volume 100% e restauração | Implementados via pactl; há teste real local e testes automatizados |
| Escala de 275% em resolução 4K | Implementada; Full HD mantém a escala |
| Steam Big Picture e outro inicializador | Implementados, com ressalvas para identificação e fechamento do processo |
| AppImage | Beta local x86_64, atualmente dependente de glibc 2.44 e de componentes gráficos externos identificados nos testes |
| Suíte automatizada | Última execução registrada: 56 testes aprovados |
| GNOME, outros compositores e X11 genérico | Adaptadores ainda planejados |
| Windows | Discussão de arquitetura; nenhum adaptador ou build Windows implementado |
| Gravação visual de combinação | Pendente; botão atual abre o TOML |
| HDR e HDMI-CEC | Código parcial/configurável; sem validação física adequada |

## Como interpretar as evidências

- **Implementado:** há código correspondente no projeto.
- **Teste automatizado:** verificações com dependências controladas; muitas
  operações de hardware e processos são simuladas.
- **Integração GTK:** widgets reais recebem sinais, mas o roteiro pode simular
  o daemon, o seletor nativo e a abertura do editor.
- **Teste real local:** executado na sessão e no equipamento do desenvolvedor.
- **Confirmação do usuário:** observação visual relatada durante a conversa.
- **Teste em contêiner:** verifica userland e carregamento; compartilha partes
  da integração do host e não certifica outra sessão gráfica completa.
- **Planejado:** proposta, ainda sem implementação/validação correspondente.

Os relatórios datados são fotografias de uma rodada. A contagem evoluiu de
35 para 39, depois 46 e finalmente 56 testes; esses números não devem ser somados.
Os 40 cenários GTK pertencem a um roteiro separado, não à contagem do unittest.

`dist/` e `.build/` são saídas locais ignoradas pelo controle de versão.
O código e os guias são a fonte durável; um binário, checksum ou log pode precisar
ser regenerado. Consulte o manifesto do artefato em uso, sem presumir que uma
reconstrução terá o mesmo SHA-256.

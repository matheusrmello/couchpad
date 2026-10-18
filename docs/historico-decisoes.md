# Histórico e decisões do projeto

[Índice da documentação](README.md)

Este é um histórico temático da conversa e do código disponível, não uma
transcrição integral nem um histórico de commits. As fases indicam ordem de
evolução; não atribuem datas ou números de versão a mudanças sem registro.

## 1. Origem e referência

A conversa começou com a solicitação de instalar o **REA**, conectá-lo ao agente
com `npx rea-agents@latest setup`, apresentar mudanças e aguardar aprovação.
Foram dadas aprovações para prosseguir. O projeto atual não reúne um log
versionado suficiente para reconstituir ou comprovar o resultado desse setup;
essa solicitação deve ser distinguida da implementação verificável do CouchPad.

Em seguida, o usuário trouxe a página do ShiftPad no winstall e perguntou sobre
engenharia reversa e uma versão Linux. O README original deste projeto registra
uma análise estática do instalador 2.2.0 e consulta a um repositório WPF público
mais antigo. Isso não equivale a observar a versão Windows em execução nem a
replicar seus detalhes internos. Não foi feita nova análise do programa Windows
na consolidação desta documentação.

Referências discutidas:

- [ShiftPad no winstall](https://winstall.app/apps/ShiftPad.ShiftPad).
- [Repositório público citado](https://github.com/APPLEVODKARUS/ShiftPad).
- [Release 2.2.0 citada](https://github.com/APPLEVODKARUS/ShiftPad/releases/tag/v2.2.0).

O CouchPad evoluiu como implementação independente em Python/GTK, sem executar
o binário Windows. Não incorpora o sistema de trial/licença mostrado na imagem
oficial. Recursos ainda ausentes não devem ser apresentados como paridade total.

## 2. Base funcional no KDE

O usuário confirmou **KDE Plasma com Wayland**. A primeira porta HDMI observada
não era a TV; depois foi conectada a Samsung. Essa distinção motivou identificar
a TV pelo EDID e não confiar somente no nome `HDMI-A-3`.

Foram implementados a troca de tela, restauração, descoberta de dispositivos e
o disparo pelo controle. O usuário confirmou a primeira troca e priorizou
**Steam Big Picture**, que relatou ter aparecido na TV.

A interface GTK e o ícone de bandeja foram implementados depois. O usuário
confirmou a janela, a bandeja e os botões **Ativar TV** e **Restaurar desktop**.

## 3. Uso do controle no PC e retorno visual

O usuário pediu uma chave persistente para desligar a automação e continuar
jogando no monitor. A chave recebeu destaque visual; o usuário confirmou que o
8BitDo não trocava a tela quando o CouchPad estava desativado e que alternar a
chave com o controle ligado funcionava.

A notificação de contagem antes da troca foi implementada a pedido do usuário,
que confirmou sua exibição. Mais tarde foram adicionados cancelamento da troca,
rearme e indicações de “aguardando botão”/“reconecte”.

A primeira intenção de empacotar em AppImage foi adiada pelo usuário até a
implementação dos recursos desejados. O empacotamento foi retomado por pedido
expresso e produziu a beta local.

## 4. Inicializadores, marca e interface

A escolha visual de outro inicializador foi implementada. O Hydra foi usado
como caso de configuração Big Picture com `--big-picture`. Para fechamento,
o usuário escolheu explicitamente **somente o inicializador, não os jogos**.

A marca passou de **ShiftPad Linux** para **couchPad**, com o SVG fornecido, e
finalmente **CouchPad**, conforme correção solicitada. Foi removido o subtítulo
com “Linux · KDE Plasma”. Os nomes internos `shiftpad_linux` e `shiftpad-linux`
foram mantidos para preservar configuração, serviços e comandos existentes.

A interface passou por duas referências fornecidas pelo usuário:

1. Mockup com navegação lateral e cartões maiores.
2. Mockup unificado com cabeçalho, resumos e três colunas, adotado no layout atual.

O usuário pediu cartões menores, janela redimensionável e ícones equivalentes
à referência. A solução inicial com ícones do tema foi substituída por SVGs
próprios coloridos, evitando depender do desenho disponível em cada tema.
A marca do projeto prevalece sobre os títulos “ShiftPad” das imagens de referência.

Arquivos de referência citados na conversa:

- `WhatsApp Image 2026-10-16 at 16.28.42.jpeg`: interface oficial apresentada.
- `couchpad.svg`: ícone fornecido pelo usuário e incorporado aos assets.
- `ShiftPad Linux – janela principal@2x.png`: primeiro mockup.
- `ShiftPad Linux – versão unificada@2x.png`: layout unificado e referência dos ícones.

As imagens originais foram mencionadas em `~/Pictures`; não são dependências
necessárias à execução e não se presume que existam em outra máquina.

## 5. Configuração e correções durante o uso

| Observação/pedido | Resultado |
|---|---|
| Identificar TV, áudio, controle e modelo | Descoberta por EDID, dados PipeWire e identidade evdev |
| Selecionar dispositivos pela janela | Combos de TV/controle/áudio, identidade persistida e atualização das listas |
| Salvar parecia não funcionar | Confirmação visível de “Preferências salvas e aplicadas” nos cartões |
| Cartão “Tela e áudio” parecia inativo | Seleção automática/manual e saída detectada passaram a ter função explícita |
| Hydra abriu mesmo com “Outro programa” desligado | Correção da seleção/configuração de inicializador; usuário confirmou abertura somente do Steam depois |
| Salvar automaticamente | Autosave com debounce, confirmação e recarga do monitor |
| Outro controle não acionou a automação | Investigação de filtro e do receptor persistente do GameSir; espera por botão no dispositivo já presente |
| Janela perdeu comunicação durante troca longa | Estado confirmado em cache durante operações locais e suspensão da varredura periódica enquanto ocupada |
| Áudio não chegou à TV em modo estendido | Identificação da porta HDMI pelo modelo e ativação do perfil estéreo, com restauração do perfil anterior |

A rodada mais recente de testes físicos confirmou um botão do 8BitDo iniciando
contagem e sessão automática. O desligamento não foi observado durante aquela
janela de teste; isso não invalida confirmações anteriores, mas não autoriza
dizer que a restauração física foi repetida em todos os aparelhos/rodadas.

## 6. Políticas de volume e escala

A pedido do usuário, foram acrescentadas duas regras fixas:

- Volume da saída escolhida para a TV em 100% a cada ativação, com restauração
  do volume anterior por canal.
- Escala 275% quando a resolução em uso é 4K; Full HD mantém a escala.

A implementação salva os valores anteriores e restaura o volume antes que o
sink HDMI desapareça. Essas regras não receberam opções próprias na janela.

## 7. GTK, AppImage e compatibilidade

Foi discutida a possibilidade de usar GTK ou Qt/PySide6. A decisão expressa foi
**manter GTK**. A biblioteca de interface não resolve, sozinha, o controle de
telas em todos os ambientes gráficos.

Foi gerado `CouchPad-0.1.0b1-x86_64.AppImage`, com Python, GTK e dependências.
Foi implementado um iniciador que cria configuração desativada no primeiro uso,
inicia um monitor próprio quando necessário e reutiliza um serviço existente.
A abertura e o encerramento foram testados fora da pasta do projeto.

Os testes com Distrobox substituíram uma expectativa teórica por evidência:
Arch exigiu dependências adicionais para o subprocesso SVG; Debian 13, Ubuntu
26.04 e Fedora 44 falharam por falta de glibc 2.44. Portanto, essa beta continua
local e não pode ser anunciada como universal. O binário esteve ausente de
`dist/` no início dessa rodada e foi reconstruído antes dos testes válidos.

## 8. Direção futura discutida

O objetivo do usuário é ampliar para famílias Arch, Debian, Fedora e outros
ambientes gráficos. A proposta é um núcleo comum com adaptadores de plataforma.
GNOME, X11 genérico, compositores Wayland e uma futura versão Windows foram
discutidos; ainda não implementados.

Windows poderá manter Python e GTK, substituindo tela, áudio, controles,
notificações, processos, IPC, caminhos e empacotamento. A intenção é um mesmo
produto com integrações específicas, não duas bases independentes.

O detalhamento e os critérios de conclusão estão em [Planos futuros](planos-futuros.md).

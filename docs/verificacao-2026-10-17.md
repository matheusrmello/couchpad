# Verificação do CouchPad — 17/10/2026

> Registro histórico desta rodada. A suíte evoluiu depois para 56 testes e
> recebeu políticas de volume/escala e empacotamento. O consolidado atual está
> em [Build e testes](build-testes.md), sem alterar as evidências abaixo.

## Resultado

- 39 testes automatizados passaram, incluindo quatro regressões novas de áudio HDMI.
- 40 verificações de integração GTK passaram, acionando sinais reais de botões, seletores e menus, com configuração temporária e serviço simulado.
- 10 verificações reais de serviço, TV, áudio, restauração e notificações passaram.
- O encerramento de um processo de inicializador foi exercitado com processos de teste reais; o outro processo permaneceu vivo.

## Problemas encontrados e corrigidos

1. **Consultas de estado durante a troca:** a janela consultava um serviço ocupado com a ativação, bloqueando o GTK e acumulando conexões no socket. Durante operações locais, agora usa o último estado confirmado e suspende a varredura periódica. A interface volta a consultar o estado quando a operação termina.
2. **Áudio ausente no modo estendido:** com monitor e TV ligados na mesma placa, o PipeWire permanecia no perfil do monitor. Agora a porta HDMI é identificada pelo modelo SAMSUNG e seu perfil estéreo é ativado. Os perfis anteriores entram no registro da sessão e são restaurados com o áudio do PC. Portas ambíguas ou indisponíveis não são escolhidas.

## Testes reais

TV Samsung em HDMI-A-3; monitor em DP-2. Os botões da janela foram acionados pelo GTK e conversaram com o serviço real.

| Fluxo | Resultado |
|---|---|
| Ativar e desativar CouchPad | Estado confirmado pelo serviço e persistido |
| Somente TV | TV ligada, monitor desligado, áudio HDMI da TV selecionado |
| Estender | TV e monitor ligados, TV posicionada à direita, áudio da TV selecionado |
| Espelhar | TV replica DP-2 (replicationSource=2), áudio da TV selecionado |
| Restaurar após cada modo | Monitor, saída de áudio e ausência de sessão pendente confirmados |
| Steam | Comando de abertura iniciado e registrado em cada sessão; comando de saída executado na restauração |
| Notificação | Enviada ao Plasma, atualizada com o mesmo ID e cancelada |
| Estado final | Automação desativada, modo Somente TV salvo, TV desativada, monitor e áudio do PC restaurados |

A saída da TV foi `alsa_output.pci-0000_04_00.0.hdmi-stereo-extra1`; a saída original foi `alsa_output.pci-0000_04_00.0.hdmi-stereo`. Os testes verificam a saída padrão e os estados do sistema; não confirmam som audível ou a aparência do Steam na TV.

## Cobertura da janela

O roteiro reproduzível está em `tools/qa_tray.py`. Usa GTK real; o daemon, a escolha no diálogo nativo e a abertura no editor são simulados. A descoberta consulta o hardware sem alterá-lo e inclui um controle de teste para validar a seleção e o salvamento dos IDs. Os casos são:

- janela não consulta serviço durante operação demorada
- janela e 9 ícones carregados
- botão Ativar CouchPad
- botão Ativar TV e bloqueio dos seletores
- botão Restaurar e desbloqueio dos seletores
- botão Desativar CouchPad
- modo de vídeo + autosave: tv-only
- modo de vídeo + autosave: extend
- modo de vídeo + autosave: mirror
- atrasos e autosave
- desligar Steam e autosave
- ligar Steam e autosave
- seleção de controle e IDs
- qualquer controle
- seleção da saída de áudio
- áudio automático
- saída de áudio manual
- detectar dispositivos e lista da TV
- seleção de TV e preservação do EDID
- cancelar escolha de programa
- recusar arquivo não executável
- escolher programa e autosave
- argumentos preservam espaços
- fechar somente inicializador
- desligar outro programa preserva Steam
- erro de argumentos aparece na janela
- recuperação após erro
- Editar combinação e Configuração completa abrem TOML
- fechar janela oculta na bandeja
- ícone da bandeja reabre janela
- menu da bandeja: Ativar CouchPad
- menu da bandeja: Ativar TV
- menu da bandeja: Restaurar desktop
- menu da bandeja: Desativar CouchPad
- menu da bandeja: Abrir CouchPad
- menu Cancelar troca para TV
- menu Fechar interface
- serviço indisponível: feedback e ações bloqueadas
- botão Iniciar serviço
- configuração original intacta

## Controle real e pendências de validação física

- O 8BitDo foi detectado durante os testes. Um botão real iniciou a contagem e a sessão automática (active=true, manual=false), com áudio na TV e comando Steam registrado. O controle permaneceu conectado durante a observação; a restauração por desligamento ainda precisa ser repetida fisicamente. Ao encerrar a rodada, o CouchPad foi desativado e o desktop foi restaurado.
- Hydra não foi aberto nesta rodada. Seleção, argumentos, chaves de ativação e isolamento do processo foram verificados com simuladores e processos de teste.
- A aparência do diálogo nativo de escolha de arquivo, a abertura do editor externo e o menu de contexto pela interação do mouse não foram verificados visualmente.
- Não há uma segunda TV para testar fisicamente a troca de alvo; a preservação do EDID e as recusas de alvo inválido foram cobertas automaticamente.
- HDR e HDMI-CEC dependem de hardware e configuração compatíveis e não foram validados fisicamente.
- “Editar combinação” abre o TOML; o gravador visual de combinação ainda não está implementado.

## Repetir verificações

```bash
python3 -m unittest discover -s tests -v
python3 tools/qa_tray.py
```

O roteiro GTK exige sessão gráfica e configuração existente. Usa uma cópia temporária e não troca a tela real nem modifica as preferências originais.

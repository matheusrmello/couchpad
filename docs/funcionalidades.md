# Guia de uso e funcionalidades

[Índice da documentação](README.md)

## Proposta do aplicativo

Jogar na TV sem reorganizar manualmente tela, áudio e inicializadores a cada
sessão. O monitor automático acompanha o controle selecionado. Quando a
ativação é permitida, apresenta uma contagem, aplica a configuração da TV e
abre os inicializadores habilitados. A restauração recupera o estado anterior.

A automação pode ficar **desativada** para usar o controle no monitor do PC.
A escolha é persistente. Reativar com o controle já presente exige um botão,
em vez de iniciar imediatamente uma sessão na TV.

## Interface atual

A interface compacta segue o mockup unificado fornecido pelo usuário:

- Cabeçalho com a marca **CouchPad** ou **CouchPad Beta**, estado e botão destacado
  para ativar/desativar a automação.
- Resumos de controle, tela ativa, áudio e inicializador.
- Três colunas com os cartões **Tela de jogo**, **Atrasos**, **Controle principal
  e ativação**, **Tela e áudio** e **Inicializadores**.
- Ícones vetoriais próprios: verde nos resumos, tela e áudio; roxo em controle
  e inicializadores; relógio laranja em atrasos. Os títulos têm fundo arredondado.
- Ações para detectar dispositivos e abrir a configuração completa.

A janela pode ser redimensionada e usa rolagem. O código define tamanho inicial
1420×900 e mínimo 1100×740; redimensionar abaixo do mínimo não é oferecido.
Esses valores são unidades da interface GTK, não uma garantia de ocupação em
pixels físicos em qualquer escala. O pedido de compactação foi atendido no
layout, mas telas pequenas e acessibilidade ainda precisam de uma matriz própria.

Fechar pelo “X” oculta a janela na bandeja. A bandeja permite abrir a janela,
alternar a automação, ativar a TV, restaurar, cancelar uma troca pendente e sair.
O comportamento de saída difere conforme quem iniciou o monitor:

| Execução | Ação de saída |
|---|---|
| Interface junto a serviço independente | **Fechar interface**; o monitor continua |
| AppImage dono de seu processo de monitor | **Encerrar CouchPad**; encerra o monitor e tenta restaurar o desktop |
| AppImage reutilizando um serviço existente | **Fechar interface**; o serviço existente é preservado |

## Fluxo de ativação

1. Confirmar a TV de destino, o controle e a saída de áudio na janela.
2. Ativar o CouchPad. Com um controle já presente, pressionar um botão.
3. Aguardar o atraso configurado; a notificação informa os segundos restantes.
4. O aplicativo salva o estado anterior, ativa a TV e aplica áudio e inicializadores.
5. Desligar/desconectar um controle que sinalize a desconexão, ou usar **Restaurar**.

Uma conexão nova pode iniciar a contagem automaticamente quando não há
combinação de botões. Uma combinação configurada exige os botões simultâneos.
Uma sessão ativada manualmente sem controle não depende de um controle para
continuar ativa. A ação **Desativar CouchPad** também restaura uma sessão pendente.

Durante a contagem, **Cancelar troca para TV** impede aquela transição. Conforme
o estado do dispositivo, um novo botão pode rearmar o fluxo; os indicadores da
interface informam quando é necessário reconectar. Alterar o destino ou
restaurar/desativar também cancela a contagem pendente.

## Controles e identificação

A descoberta lista modelo informado pelo driver, vendor ID, product ID,
identificador `uniq` quando disponível, barramento e caminho `/dev/input/event*`.
A seleção aceita **Qualquer controle** ou um dispositivo específico. O filtro
salvo combina nome, IDs e `uniq`; não depende somente do número `eventN`.

Equipamentos usados na conversa:

- **8BitDo Ultimate 2 Wireless Controller**, IDs observados `2dc8:310b`.
- **GameSir G4 Pro**, com receptor que pode continuar exposto mesmo desligado.

O nome é a identificação fornecida pelo sistema. Não há uma base universal de
modelos nem garantia de distinguir dispositivos que se apresentam com a mesma
identidade. A seleção “Qualquer controle” continua acompanhando um candidato
por vez; não é uma implementação de sessões independentes por jogador.

### Receptores que permanecem conectados

Um receptor USB pode continuar em `/dev/input` após desligar o controle. Quando
o dispositivo já está presente ao iniciar/reativar o monitor, o aplicativo
aguarda entrada de botão. Isso permitiu o uso do GameSir observado.

Se o receptor não informa a desconexão, o aplicativo não pode deduzi-la de forma
confiável pela mera presença do dispositivo. Use **Restaurar**. Não há um prazo
de inatividade tratado como prova de que o controle foi desligado, nem uma
regra universal específica para todo receptor recém-plugado.

## Tela e escala

| Opção | Efeito |
|---|---|
| Somente TV (`tv-only`) | Ativa a TV e desativa as outras saídas ativas |
| Estender (`extend`) | Mantém o desktop e posiciona a TV à direita dele |
| Espelhar (`mirror`) | Configura a TV para replicar o monitor principal |

A TV é vinculada ao SHA-256 do EDID quando disponível. A troca é recusada se
outro aparelho ocupar o conector com identidade diferente. Monitor principal
e destino precisam estar conectados; o desktop deve estar ativo antes da troca.
A interface bloqueia a troca de dispositivos enquanto a sessão está ativa.

**Política de escala atual, sem chave própria na interface:**

- Resolução em uso de 3840×2160 ou 4096×2160: escala **2,75 (275%)**.
- Full HD: não altera a escala existente.
- A resolução e a taxa de atualização não são escolhidas automaticamente.
- A resolução do modo atual prevalece sobre a simples existência de um modo
  4K na lista: uma TV operando em 1080p não recebe 275% só por oferecer 4K.
- A escala anterior é incluída na restauração, inclusive para uma TV que
  estava desativada antes da sessão.

O tratamento de HDR/WCG e brilho SDR conserva propriedades reportadas pelo
KScreen quando há capacidade. Não é uma promessa de suporte HDR em todo
aparelho; a validação física desse caminho continua pendente.

## Áudio e volume

O cartão permite selecionar a saída da TV, escolher **Automático** ou informar
um nome de sink. Algumas saídas HDMI só aparecem depois de ativar a tela.

A detecção automática usa identidade/modelo da TV, saídas HDMI novas e, quando
necessário, um perfil HDMI estéreo disponível cuja porta corresponda ao modelo.
Uma identificação ambígua não deve selecionar uma saída arbitrária. A janela
consegue apresentar a associação registrada na sessão mesmo quando o driver
usa um nome genérico como “HDMI 1”.

Ao escolher a saída:

- Define essa saída como padrão.
- Salva o volume anterior por canal e coloca a saída em **100%**.
- Salva perfis de áudio alterados e restaura perfis, saída padrão e volumes ao voltar.
- Restaura o volume da TV antes de desativar o HDMI, pois o sink pode desaparecer.

O volume é o do dispositivo de áudio no PipeWire/PulseAudio, não o volume físico
ajustado pelo controle remoto da TV. A implementação não desativa explicitamente
mute. Também não percorre/move explicitamente os fluxos de áudio já abertos;
a política do servidor e do aplicativo influencia fluxos existentes.

## Steam e outros inicializadores

Steam usa `steam://open/bigpicture` e `steam://close/bigpicture`, com o executável
atual configurado em `/usr/bin/steam`. A intenção é sair do Big Picture ao
restaurar, mantendo o cliente Steam aberto. Instalações Flatpak e caminhos
alternativos ainda precisam de descoberta específica.

**Outro programa** aceita executável, AppImage ou `.desktop`. Os argumentos são
separados com `shlex`, sem shell. O Hydra foi configurado na conversa com
`--big-picture`. Steam e outro programa têm chaves independentes e podem ser
usados juntos. Desativar “Outro programa” mantém o caminho salvo, mas não o abre.

**Fechar outro programa ao restaurar** atende à decisão de fechar somente o
inicializador, preservando os jogos. O processo é identificado por PID, boot ID
e instante de criação. Não é enviado sinal a um PID reutilizado nem a um grupo
inteiro de processos.

Limitações: `.desktop` não oferece processo rastreável para essa função; se um
launcher transfere o pedido a uma instância já aberta e termina, o CouchPad
não controla essa instância. SIGTERM é uma solicitação, não uma confirmação de
que qualquer launcher encerrou. Não há rastreamento de jogos para aguardar sua saída.

## Autosave e ajustes avançados

As alterações editáveis pela janela são salvas automaticamente. Interruptores
aguardam aproximadamente 100 ms; demais alterações usam normalmente 550 ms,
com nova tentativa se a interface estiver ocupada. A confirmação ou a falha
aparece nos cartões. Os atrasos aceitam 0 a 300 segundos; a janela usa passo de 0,5 s.

**Editar combinação** e **Configuração completa** abrem o TOML no aplicativo
associado. O gravador visual de combinação ainda não existe. HDMI-CEC aceita
comandos avançados configurados no arquivo e exige ferramenta/adaptador apropriados.

# Configuração e operação

[Índice da documentação](README.md)

## Pré-requisitos atuais

Para executar pelo código: Python 3.11+, `evdev`, PyGObject, GTK 3, cairo e
bibliotecas/typelibs correspondentes. Para controlar o hardware: KDE
Plasma/Wayland, `kscreen-doctor`, `pactl`, servidor de áudio acessível e leitura
dos eventos do controle. A janela usa X11/XWayland. A bandeja no Plasma foi
usada com `xembedsniproxy`.

`notify-send` e `gdbus` servem às notificações. `xdg-open` abre o TOML;
`gio` abre atalhos `.desktop`. Steam e Hydra precisam estar instalados
separadamente. HDMI-CEC exige sua própria ferramenta e hardware compatível.

O AppImage inclui o runtime Python/GTK, mas preserva os requisitos de integração
do host e as limitações de glibc/carregamento de imagens descritas em
[Build e testes](build-testes.md).

## Primeiro uso

### AppImage

Sem argumentos, abre a interface e tenta iniciar/reutilizar o monitor.
Na falta de configuração, identifica o monitor ativo e escolhe outra saída
conectada como **candidata** a TV. Isso não prova que o segundo painel é uma TV:
confirme a seleção na janela. Se só houver um monitor, usa um destino provisório
`TV-NOT-CONFIGURED`, selecionável depois da conexão da TV.

O arquivo novo tem automação desativada, áudio automático, qualquer controle e
nenhum inicializador ligado. Um arquivo existente não é sobrescrito.

### Código-fonte

O comando `tray` não é o assistente de primeiro uso do AppImage. Prepare o
TOML antes. `config.example.toml` contém os nomes/EDID do equipamento de
desenvolvimento e não deve ser copiado sem adaptação para outro computador.

## Exemplo de configuração sem identidade de uma máquina real

O exemplo abaixo é estrutural. Substitua `MONITOR` e `TV` pelos nomes reais
reportados por `doctor`; conectores distintos são obrigatórios.

```toml
[general]
enabled = false

[display]
desktop_output = "MONITOR"
tv_output = "TV"
tv_edid_sha256 = ""
mode = "tv-only"

[audio]
tv_sink = ""

[gamepad]
name_contains = ""
vendor_id = ""
product_id = ""
uniq = ""
activation_buttons = []
connect_delay = 2.0
disconnect_delay = 2.0

[launcher]
start = []
stop = []
custom_path = ""
custom_enabled = false
custom_close = false
custom_args = []

[cec]
on = []
off = []
```

## Referência de campos

| Seção/chave | Semântica e validação |
|---|---|
| `general.enabled` | Booleano persistente; false impede acionamento automático |
| `display.desktop_output` | Conector do monitor, distinto da TV; alteração avançada no TOML |
| `display.tv_output` | Conector escolhido como destino |
| `display.tv_edid_sha256` | Vazio ou hash hexadecimal de 64 caracteres; verifica a identidade do painel |
| `display.mode` | `tv-only`, `extend` ou `mirror` |
| `audio.tv_sink` | Vazio para automático ou nome exato do sink selecionado |
| `gamepad.name_contains` | Filtro textual do nome; vazio aceita qualquer nome compatível |
| `gamepad.vendor_id` / `product_id` | IDs hexadecimais de quatro caracteres; ambos preenchidos ou ambos vazios |
| `gamepad.uniq` | Identidade única quando exposta pelo driver; opcional |
| `gamepad.activation_buttons` | Lista de nomes `BTN_*` suportados pelo evdev, pressionados simultaneamente |
| `gamepad.connect_delay` / `disconnect_delay` | Números entre 0 e 300 segundos |
| `launcher.start` / `stop` | Listas de argumentos para comandos de início/fim; a chave Steam usa pares conhecidos |
| `launcher.custom_path` | Caminho absoluto do executável/AppImage/`.desktop` quando habilitado |
| `launcher.custom_enabled` | Chave independente do Steam; false mantém o caminho sem executá-lo |
| `launcher.custom_close` | Fechamento do processo próprio; incompatível com `.desktop` habilitado |
| `launcher.custom_args` | Lista de argumentos; `.desktop` não aceita argumentos adicionais |
| `cec.on` / `off` | Comandos opcionais como listas de argumentos |

No modelo atual, **volume 100%** e **escala 275% em 4K** são políticas fixas,
sem campos TOML próprios. Não inventar opções como `tv_volume` ou `tv_scale`:
elas não são reconhecidas pela implementação.

A janela edita os campos correspondentes e preserva ajustes avançados. Uma
configuração customizada em `launcher.start` não é automaticamente substituída
pela chave Steam; o aplicativo pode bloquear essa chave para preservar o comando.

Para Hydra, o campo de argumentos da janela pode receber `--big-picture`.
No arquivo, isso corresponde a `custom_args = ["--big-picture"]`. Só habilite
`custom_close` para executável rastreável e tenha em conta o reuso de instâncias.

## CLI

A partir da raiz do código-fonte:

```bash
python3 -m shiftpad_linux --version
python3 -m shiftpad_linux doctor
python3 -m shiftpad_linux devices
python3 -m shiftpad_linux preview
python3 -m shiftpad_linux status
```

| Comando | Efeito |
|---|---|
| `doctor` | Diagnóstico e plano; não troca telas |
| `devices` | Descoberta detalhada em JSON; não troca telas |
| `preview` | Mostra o plano e inicializadores sem aplicá-los |
| `status` | Consulta o monitor pelo socket |
| `enable` / `disable` | Persiste a automação; desativar também restaura sessão pendente |
| `switch` | Ativa a TV conforme o perfil |
| `restore` | Restaura uma sessão pendente |
| `cancel` | Cancela uma troca automática pendente |
| `run` | Mantém o monitor de controle em execução |
| `tray` | Abre a interface e bandeja, sem criar por si só o perfil inicial |

`switch`, `restore`, `enable` e `disable` usam o monitor existente quando há
socket; sem ele, os caminhos suportados executam sob o lock de instância.
Ao executar `run`, Ctrl+C solicita a restauração antes da saída.

O parâmetro global vem **antes** do subcomando:

```bash
python3 -m shiftpad_linux --config /caminho/config.toml doctor
```

A opção `--config` é usada por operações da CLI/monitor, mas não redireciona
automaticamente o socket nem todos os caminhos da interface. Não usá-la como
isolamento completo de uma segunda instância. Os testes de primeiro uso usam
diretórios XDG próprios, com automação desativada, e cuidam também de socket/estado.

O AppImage aceita os mesmos argumentos; sem argumentos usa `portable.main()`.
Também oferece `--runtime-check`, que importa GTK/cairo/evdev e carrega os SVGs,
sem iniciar uma sessão de jogo. Para contêiner sem FUSE, acrescente
`--appimage-extract-and-run` antes desses argumentos.

## Serviços de usuário existentes

- `shiftpad-linux.service`: monitor de controle.
- `shiftpad-linux-tray.service`: janela e bandeja.

Os arquivos em `systemd/` usam `%h/Documents/shitPad-rea` e `/usr/bin/python3`.
São exemplos ligados à instalação de desenvolvimento, não unidades portáteis
para qualquer diretório ou AppImage. O AppImage tem sua própria supervisão e
não exige instalar essas unidades.

Consultas úteis, sem alterar a sessão:

```bash
systemctl --user status shiftpad-linux.service shiftpad-linux-tray.service
journalctl --user -u shiftpad-linux.service -n 50 --no-pager
journalctl --user -u shiftpad-linux-tray.service -n 50 --no-pager
```

Editar o TOML enquanto o monitor está aberto requer recarga para surtir efeito.
A janela já envia `reload` ao salvar. Para uma edição avançada, a recarga local
pode ser solicitada pelo cliente Python:

```bash
python3 -c 'from shiftpad_linux.control import request; print(request("reload"))'
```

Não há subcomando público `reload` na CLI nesta versão. Reiniciar um serviço
pode restaurar/interromper a sessão e não deve ser tratado como consulta inócua.

## Diagnóstico por sintoma

| Sintoma | Verificações |
|---|---|
| Controle ausente | `devices`, conexão, modo do controle e permissões dos eventos; ausência na lista não comprova desconexão física |
| Controle presente sem ativar | Chave da automação, filtro/IDs, combinação e mensagens de espera por botão/reconexão |
| GameSir desliga e TV permanece | Receptor pode continuar exposto; usar Restaurar e consultar a limitação do receptor |
| TV recusada | Cabo, conector, EDID salvo e monitor ativo; detectar novamente após mudança física |
| Áudio da TV não aparece antes de ativar | Pode depender da saída HDMI ativa ou de perfil da placa; manter Automático/nome salvo e observar o diagnóstico |
| Som não muda em aplicativo já aberto | Verificar saída padrão e política dos fluxos existentes; o CouchPad não move cada fluxo explicitamente |
| Outra saída de áudio escolhida | Conferir `tv_sink`, modelo da TV, porta e ambiguidade |
| Hydra abre com a chave desligada | Conferir também `launcher.start`; há dois caminhos de inicializador, não só `custom_enabled` |
| Janela não abre no AppImage | `--version`, `--runtime-check`, glibc, dependências do SVG e requisitos de KDE |
| `GLIBC_2.44 not found` | Incompatibilidade deste build; requer reconstrução numa base mais antiga para suportar esse sistema |
| Erro no carregador SVG | Limitação de dependências do sandbox Glycin confirmada nos testes de Arch; não confundir com erro do código de automação |
| Falha após troca interrompida | Verificar o estado pendente e usar o caminho de restauração; não apagar `session.json` antes de recuperar o desktop |

A instalação de ferramentas e as permissões de entrada dependem da distribuição.
Não há instalador universal de dependências nem correção automática de udev.
Logs de diagnóstico podem conter modelo/ID dos dispositivos e caminhos locais;
revise-os ao publicar um relato de erro.

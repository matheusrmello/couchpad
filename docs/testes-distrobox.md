# CouchPad — testes com Distrobox

> Registro do empacotamento anterior com glibc 2.44. A reconstrução de
> 06/11/2026 usa glibc 2.36 e adiciona Flatpak; consulte
> [o relatório atualizado](reconstrucao-2026-11-06.md).

[Índice da documentação](README.md) · [Build e compatibilidade](build-testes.md)

Os testes foram executados usando Distrobox 1.8.2.5 com Podman rootless.
DistroShelf já está instalado no host e pode gerenciar estes mesmos contêineres.

## Resultado da beta 0.1.0b1

| Ambiente | glibc observada | Versão do AppImage | Runtime GTK/SVG |
|---|---|---|---|
| Arch Linux atualizado | 2.44 | Passou | Passou após instalar librsvg e fontconfig |
| Debian 13 (trixie) | 2.41 | Falhou | Falhou: GLIBC_2.44 ausente |
| Ubuntu 26.04.1 LTS | 2.43 | Falhou | Falhou: GLIBC_2.44 ausente |
| Fedora Linux 44 | 2.43 | Falhou | Falhou: GLIBC_2.44 ausente |

No Arch sem as dependências adicionais, o comando de versão passou, mas o
carregador SVG saiu com código 127. A inspeção do auxiliar `glycin-svg`
identificou `librsvg-2.so.2` e `libcairo.so.2` ausentes no sistema do contêiner;
também faltava configuração de fontconfig. Após instalar librsvg e fontconfig
apenas nesse ambiente, o runtime confirmou GTK 3.24, cairo, evdev e os oito SVGs.

O pacote contém essas bibliotecas, mas o subprocesso isolado de imagens usa
bibliotecas do sistema. Portanto, ainda existe uma dependência externa efetiva.
O teste confirmou que a compatibilidade do Arch também precisa desses ajustes;
a presença de glibc 2.44, sozinha, não garante o funcionamento.

Nos outros três sistemas, a falha ocorreu antes da interface, no carregamento
do módulo math do Python empacotado: ele exige símbolos GLIBC_2.44.

## Procedimento e preservação do host

- Cada contêiner recebeu um diretório pessoal próprio em `.build/distrobox/homes/`.
- A pasta `dist/` foi montada somente para leitura em `/opt/couchpad-beta`.
- Foram usados `--version` e `--runtime-check`, com extração do AppImage para
  evitar dependência de FUSE dentro dos contêineres.
- Não foi iniciada a automação, nem alterados vídeo, áudio ou preferências.
- O AppImage estava ausente no início e foi reconstruído pelo roteiro existente
  antes da rodada válida. As falhas iniciais por arquivo ausente não são usadas
  como evidência de incompatibilidade.
- Os ambientes ficam parados ao final, disponíveis para repetir os testes.

## Ambientes criados

- `couchpad-qa-arch`
- `couchpad-qa-debian13`
- `couchpad-qa-ubuntu2604`
- `couchpad-qa-fedora44`

Para repetir, a partir da raiz do projeto:

```bash
python3 tools/test_appimage_distrobox.py
```

O roteiro cria os ambientes ausentes e executa as verificações. Para um único
ambiente, acrescente `arch`, `debian`, `ubuntu` ou `fedora`. Os pacotes extras
instalados no Arch persistem nesse contêiner, então o resultado inicial do Arch
limpo foi preservado separadamente em `.build/distrobox/arch-clean-results.json`.

Logs completos: `.build/distrobox/logs/`. Dados resumidos:
`dist/distrobox-results.json`.

## Limites e próximos passos

Esses resultados verificam o carregamento e as dependências do pacote. Não
validam uma sessão gráfica independente de cada distribuição: Distrobox
compartilha a integração gráfica, áudio e kernel com o host. A automação em
GNOME, outros compositores, drivers e hardware diferentes ainda requer sessões
próprias, máquinas virtuais e/ou hardware real. Ambientes aninhados ajudam a
testar adaptadores, mas não substituem a validação de HDMI físico.

Para ampliar a distribuição, reconstruir numa base com glibc mais antiga e
resolver o isolamento das dependências do carregador de imagens. Depois,
repetir esta matriz e os testes de sessão gráfica.

Referências: https://distrobox.it/usage/distrobox-create/ e
https://github.com/ranfdev/DistroShelf.

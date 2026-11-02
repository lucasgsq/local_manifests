# Quark — A11+KSU

Branch padrao para builds Android 11 / LineageOS 18.1: **A11+KSU**, variante `user`, SELinux **Enforcing**, KernelSU integrado. O usuario validou boot, camera, WiFi, audio, GPS, sensores, USB, carregamento e o retorno das metricas do overlay ate a etapa 35. Telefonia e dados moveis ainda aguardam validacao.

## Branches mantidos

- `A11+KSU`: padrao Android 11.
- `A12+`: bring-up Android 12.

Os repositorios proprios selecionados por este manifesto usam o mesmo nome de branch, incluindo media/display. Nesses dois repositorios a consolidacao apenas cria referencias ao mesmo codigo legado anteriormente selecionado; nao adiciona patches de compatibilidade Android 12. Os branches antigos A11/A11+ foram substituidos.

## Atualizar uma arvore existente

Siga [SELINUX_UPDATES.md](SELINUX_UPDATES.md) antes de sincronizar uma arvore que recebeu os aplicadores das etapas. O preparador faz backup e stash seletivo dos patches ja publicados, preservando a configuracao local de assinatura. Nao reaplique esses stashes apos o sync. Nao use descarte forcado de alteracoes locais.

Com o repositorio do manifesto no branch `A11+KSU`, atualize-o antes do proximo repo sync:

```bash
cd ~/android/lineage18
git -C .repo/local_manifests pull --ff-only origin "A11+KSU"
python3 .repo/local_manifests/prepare-sync.py
python3 .repo/local_manifests/prepare-sync.py --apply
repo sync -j4
bash .repo/local_manifests/build-quark.sh
```

O build seleciona o OUT_DIR absoluto da arvore e registra as revisoes utilizadas. O script recusa SELINUX_IGNORE_NEVERALLOWS habilitado. Chaves privadas e arquivos de build nao sao fornecidos pelo repositorio. A assinatura particular continua configurada localmente.

## Informacoes adicionais

- [SELinux, migracao e limites da validacao](SELINUX_UPDATES.md).
- [Origem e commits preservados de media/display](SOURCE_PROVENANCE.md).
- [Kernel Adiutor como aplicativo opcional](OPTIONAL_APPS.md).

`patches.sh`/`patches.py` continuam disponiveis para os commits legados de media/display; o plano busca os branches atuais dos repositorios proprios. Os commits ja estao incluidos nos projetos selecionados pelo manifesto.

Negativas de camera_prop, DAC termico e restricoes do AIDA64 continuam em investigacao. Normalizacao da temperatura nao comprova que todos os caminhos termicos estejam validados.

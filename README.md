# Quark â€” A12+

Branch experimental para Android 12L / LineageOS 19.1, API 32. Mantem os commits proprios de bring-up e o permissive temporario em `userdebug`/`eng`; builds `user` permanecem Enforcing. Build completa e validacao no aparelho Android 12 continuam pendentes.

## Branches mantidos

- `A11+KSU`: padrao Android 11.
- `A12+`: bring-up Android 12.

Os repositorios proprios selecionados por este manifesto usam o mesmo nome de branch, incluindo media/display. Nesses dois repositorios a consolidacao apenas cria referencias ao mesmo codigo legado anteriormente selecionado; nao adiciona patches de compatibilidade Android 12. Os branches antigos A11/A11+ foram substituidos.

## Atualizar uma arvore existente

Siga [SELINUX_UPDATES.md](SELINUX_UPDATES.md) antes de sincronizar uma arvore que recebeu os aplicadores das etapas. O preparador faz backup e stash seletivo dos patches ja publicados, preservando a configuracao local de assinatura. Nao reaplique esses stashes apos o sync. Nao use descarte forcado de alteracoes locais.

A pasta .repo/local_manifests pode conter apenas XMLs baixados, sem um clone Git. Nesse caso git pull nao funciona. O instalador abaixo atende ambos os formatos: preserva integralmente a pasta antiga em .repo/local_manifests-before-DATA, cria um clone Git do branch selecionado e preserva as entradas XML particulares, removendo somente as entradas gerenciadas que seriam duplicadas. Em seguida confere e guarda os patches locais ja publicados.

```bash
(
set -e
cd ~/android/lineage19
curl -fL "https://raw.githubusercontent.com/lucasgsq/local_manifests/A12+/instalar-manifesto-quark.py" -o /tmp/instalar-manifesto-quark.py
python3 /tmp/instalar-manifesto-quark.py --branch "A12+" --apply
repo sync -j1 --fail-fast hardware/qcom-caf/apq8084/media hardware/qcom-caf/apq8084/display device/motorola/quark kernel/motorola/apq8084 vendor/motorola device/qcom/sepolicy-legacy system/sepolicy device/lineage/sepolicy
bash .repo/local_manifests/build-quark.sh
)
```

O bloco para imediatamente se qualquer passo falhar. Nao continue o sync ou build depois de um erro; envie a primeira mensagem. Nenhum reset, clean ou checkout forcado e executado.

O build seleciona o OUT_DIR absoluto da arvore e registra as revisoes utilizadas. O script recusa SELINUX_IGNORE_NEVERALLOWS habilitado. Chaves privadas e arquivos de build nao sao fornecidos pelo repositorio. A assinatura particular continua configurada localmente.

## Informacoes adicionais

- [SELinux, migracao e limites da validacao](SELINUX_UPDATES.md).
- [Origem e commits preservados de media/display](SOURCE_PROVENANCE.md).
- [Kernel Adiutor como aplicativo opcional](OPTIONAL_APPS.md).

`patches.sh`/`patches.py` continuam disponiveis para os commits legados de media/display; o plano busca os branches atuais dos repositorios proprios. Os commits ja estao incluidos nos projetos selecionados pelo manifesto.

Negativas de camera_prop, DAC termico e restricoes do AIDA64 continuam em investigacao. Normalizacao da temperatura nao comprova que todos os caminhos termicos estejam validados.

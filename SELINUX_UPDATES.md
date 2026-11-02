# Consolidacao SELinux ate a etapa 35

Branch: A11+KSU. SDK esperado: 30.

Android 11 user/Enforcing validado no Quark, com camera, audio, GPS, sensores, KernelSU, USB e carregamento conforme o baseline. O usuario confirmou o retorno dos indicadores do overlay e temperatura aos niveis anteriores na etapa 35. Telefonia/dados moveis ainda aguardam validacao.

Inclui device tree, politica Qualcomm legada, politica de plataforma, perfil Lineage HAL1 e quatro blobs de camera corrigidos. Os forks sao selecionados juntos pelo manifesto. O kernel ja apontava para o branch correto e nao recebeu mudancas novas nesta consolidacao. Nao inclui chaves privadas, OUT_DIR compilado, logs pessoais ou stashes. O Qcom A12+ mantem a base lineage-18.1-legacy usada pelo manifesto A12.

## Atualizar uma arvore que recebeu os patches locais

Nao execute repo sync diretamente sobre os patches locais sem preserva-los. A ferramenta abaixo verifica hashes e guarda somente os arquivos publicados, com backup em ~/quark-sync-backups e stash por repositorio. Editos diferentes dos publicados provocam recusa antes de qualquer alteracao. lineage_quark.mk com a configuracao particular de assinatura fica fora da lista, assim como as chaves privadas. Outros arquivos particulares nao sao guardados nem descartados.

```bash
cd ~/android/lineage18
git -C .repo/local_manifests pull --ff-only origin A11+KSU
python3 .repo/local_manifests/prepare-sync.py
python3 .repo/local_manifests/prepare-sync.py --apply
repo sync -j4 device/motorola/quark vendor/motorola device/qcom/sepolicy-legacy system/sepolicy device/lineage/sepolicy
bash .repo/local_manifests/build-quark.sh
```

A linha pull pressupoe que o repositorio do manifesto ja esteja no branch A11+KSU. Para uma arvore nova, selecione esse branch antes do sync, sem executar o preparador de stashes. Nao reaplique os stashes apos o sync: as mesmas alteracoes estao nos commits. Os backups e os identificadores de stash permanecem disponiveis para recuperacao; nao sao apagados automaticamente. Se a ferramenta recusar uma divergencia, revise-a antes de prosseguir. Nao use reset --hard, clean ou sync com descarte forcado.

O build usa OUT_DIR absoluto para evitar gerar os headers dentro do kernel. Padrao: out-user-policy, variante user. JOBS=4 pode reduzir paralelismo. BUILD_VARIANT pode selecionar user/userdebug/eng, respeitando a politica de bring-up descrita acima. Registra quark-build-sources.json e o log de compilacao. Nao usa SELINUX_IGNORE_NEVERALLOWS, nao instala ou faz flash. A pasta de saida pode ser reutilizada sem limpeza; algumas regras podem ser regeneradas pelos novos caminhos/revisoes.

## Pendencias que esta consolidacao nao declara resolvidas

Negativas DAC do thermal-engine e leituras de camera_prop ainda exigem investigacao. A temperatura ter normalizado nao prova que todos os caminhos termicos estao validados. AIDA64 usa untrusted_app e nao recebe a permissao do overlay; o namespace OpenCL e outra questao. O indicador RAM do overlay continua baseado em qcom,cpubw.35 com conversao legada. Os neverallows e snapshots foram customizados para o perfil HAL1: passar os testes locais nao equivale a aprovar CTS ou preservar o contrato AOSP sem customizacoes.

## Referencias de rollback

Os commits anteriores e novos, com hashes dos arquivos publicados, estao em selinux-sync-plan.json. Use reversoes coordenadas dos repositorios e do manifesto; reverter apenas um componente pode quebrar os tipos, contextos ou a camera. Nenhum historico foi reescrito.

QUARK_OUT_DIR permite escolher outra pasta explicitamente. O script ignora um OUT_DIR herdado de outra arvore para evitar misturar saidas Android 11 e Android 12.

## Consolidacao dos nomes de branch

Atualize este manifesto antes de repo sync: media e display agora usam `A11+KSU`, preservando os mesmos commits. Os branches antigos foram removidos dos repositorios proprios de build. A11+KSU e o padrao dos repositorios; A12+ permanece experimental.

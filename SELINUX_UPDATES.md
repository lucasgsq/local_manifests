# Consolidacao SELinux ate a etapa 35

Branch: A12+. SDK esperado: 32.

Port para LineageOS 19.1/Android 12L. Preserva os commits especificos do A12+ e o permissive temporario do bring-up em userdebug/eng; user permanece enforcing conforme o BoardConfig anterior. Nao foi realizada build completa nem validacao de hardware Android 12. As mudancas de plataforma foram adaptadas a API 32, sem copiar snapshots Android 11 ou alterar snapshots anteriores.

Inclui device tree, politica Qualcomm legada, politica de plataforma, perfil Lineage HAL1 e quatro blobs de camera corrigidos. Os forks sao selecionados juntos pelo manifesto. O kernel ja apontava para o branch correto e nao recebeu mudancas novas nesta consolidacao. Nao inclui chaves privadas, OUT_DIR compilado, logs pessoais ou stashes. O Qcom A12+ mantem a base lineage-18.1-legacy usada pelo manifesto A12.

## Atualizar uma arvore que recebeu os patches locais

Nao execute repo sync diretamente sobre os patches locais sem preserva-los. A ferramenta abaixo verifica hashes e guarda somente os arquivos publicados, com backup em ~/quark-sync-backups e stash por repositorio. Editos diferentes dos publicados provocam recusa antes de qualquer alteracao. lineage_quark.mk com a configuracao particular de assinatura fica fora da lista, assim como as chaves privadas. Outros arquivos particulares nao sao guardados nem descartados.

```bash
(
set -e
cd ~/android/lineage19
curl -fL "https://raw.githubusercontent.com/lucasgsq/local_manifests/A12+/instalar-manifesto-quark.py" -o /tmp/instalar-manifesto-quark.py
python3 /tmp/instalar-manifesto-quark.py --branch "A12+" --apply
python3 .repo/local_manifests/concluir-sync-quark.py --branch "A12+" --apply
bash .repo/local_manifests/build-quark.sh
)
```

Nao e necessario que local_manifests ja seja Git. O instalador preserva a pasta anterior integralmente em .repo/local_manifests-before-DATA, fora da pasta ativa. XMLs particulares sao mantidos e excluidos de commits acidentais; as entradas dos projetos gerenciados sao substituidas pelo manifesto atual para evitar duplicatas. O clone novo permite git pull nas proximas atualizacoes.

Nao reaplique os stashes apos o sync: as mesmas alteracoes estao nos commits. Backups e stashes permanecem disponiveis; se alguma conferencia falhar, pare e revise a mensagem antes de sincronizar. Nao use reset --hard, clean ou descarte forcado.

O build usa OUT_DIR absoluto para evitar gerar os headers dentro do kernel. Padrao: out-a12-policy, variante userdebug. JOBS=4 pode reduzir paralelismo. BUILD_VARIANT pode selecionar user/userdebug/eng, respeitando a politica de bring-up descrita acima. Registra quark-build-sources.json e o log de compilacao. Nao usa SELINUX_IGNORE_NEVERALLOWS, nao instala ou faz flash. A pasta de saida pode ser reutilizada sem limpeza; algumas regras podem ser regeneradas pelos novos caminhos/revisoes.

## Pendencias que esta consolidacao nao declara resolvidas

Negativas DAC do thermal-engine e leituras de camera_prop ainda exigem investigacao. A temperatura ter normalizado nao prova que todos os caminhos termicos estao validados. AIDA64 usa untrusted_app e nao recebe a permissao do overlay; o namespace OpenCL e outra questao. O indicador RAM do overlay continua baseado em qcom,cpubw.35 com conversao legada. Os neverallows e snapshots foram customizados para o perfil HAL1: passar os testes locais nao equivale a aprovar CTS ou preservar o contrato AOSP sem customizacoes.

## Referencias de rollback

Os commits anteriores e novos, com hashes dos arquivos publicados, estao em selinux-sync-plan.json. Use reversoes coordenadas dos repositorios e do manifesto; reverter apenas um componente pode quebrar os tipos, contextos ou a camera. Nenhum historico foi reescrito.

QUARK_OUT_DIR permite escolher outra pasta explicitamente. O script ignora um OUT_DIR herdado de outra arvore para evitar misturar saidas Android 11 e Android 12.

## Consolidacao dos nomes de branch

Atualize este manifesto antes de repo sync: media e display agora usam `A12+`, preservando os mesmos commits. Os branches antigos foram removidos dos repositorios proprios de build. A11+KSU e o padrao dos repositorios; A12+ permanece experimental.

## Troca de metadados dos forks de politica

O preparador guarda os patches locais. O novo concluir-sync-quark.py preserva tambem os historicos e stashes dos tres projetos de politica em bundles verificados, com copias de configuracao Git e arquivos nao rastreados em ~/quark-sync-backups/metadata-DATA. Recusa alteracoes rastreadas ainda pendentes. Primeiro tenta repo sync normal; somente se o repo identificar incompatibilidade dos metadados ao trocar para os forks, executa --force-sync no projeto de politica indicado. Nunca usa --force-checkout e nao forca device, vendor ou kernel. Outros erros interrompem a operacao.

Se o instalador e o prepare-sync.py ja terminaram, nao os execute novamente apenas por esse erro. Atualize este repositorio Git com pull --ff-only e execute concluir-sync-quark.py --branch "A12+" --apply. Nao reaplique os stashes: as mesmas alteracoes estao publicadas. A migracao nao instala imagens no aparelho.

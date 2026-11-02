# Campo de backports de seguranca

Em Configuracoes > Sobre o telefone > Versao do Android, o campo aparece depois do nivel de seguranca do fabricante.

- A11+KSU: outubro de 2026, referente aos lotes R_asb_2026-09 e R_asb_2026-10 conferidos no historico da base local (79 + 5 alteracoes).
- A12+: Nao verificado. A auditoria de Android 11 nao se transfere para Android 12L.

Os niveis oficiais Android/fabricante permanecem intactos. O campo nao certifica cobertura completa dos boletins, nao afirma que firmware/kernel receberam todos os fixes, e nao e calculado pela data de compilacao. Fontes e limites da auditoria estao em device/motorola/quark/security/.

A propriedade visual e o recurso config_lineageSecurityBackportMonth no overlay de Settings da device tree. So atualizar apos auditoria; limpar se a nova base nao corresponder a ela.

## Atualizacao de uma base existente

Na raiz da arvore Ubuntu, execute:

```sh
git -C .repo/local_manifests pull --ff-only origin 'A11+KSU'
python3 .repo/local_manifests/concluir-sync-quark.py --branch 'A11+KSU'
python3 .repo/local_manifests/concluir-sync-quark.py --branch 'A11+KSU' --apply
bash .repo/local_manifests/build-quark.sh
```

O helper preserva o historico de Settings em bundle antes da eventual troca de metadados pelo fork. Exige os projetos de metadados sem alteracoes rastreadas. Nao usa --force-checkout. O revert local em vendor/lineage nao e tocado.

Instalar a ROM completa; um boot.img nao atualiza Settings. Confirmar a nova linha e as duas datas oficiais anteriores. A12+ deve mostrar Nao verificado. A compilacao e a tela em runtime devem ser validadas no aparelho.

## Manutencao

O fork de Settings usa lineage-18.1 no A11+KSU e lineage-19.1 no A12+. Ele precisa incorporar atualizacoes futuras do upstream: um fork nao recebe correcoes automaticamente. Nao substituir a base A12+ pela base Android 11.

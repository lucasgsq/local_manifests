# Checagem automatica dos backports

A cada execucao de build-quark.sh, antes de lunch e Soong, check-security-backports.py consulta o Gerrit publico da LineageOS e confere os lotes contra o historico local. Nao e necessario editar o mes manualmente.

O A11+KSU consulta somente lineage-18.1/R_asb_*. O A12+ consulta somente lineage-19.1/S_asb_*. O intervalo comeca em agosto de 2025. Sao conferidos todos os lotes publicados encontrados no intervalo, ate o ultimo lote verificavel. Um lote anterior pendente bloqueia o avanco; propostas abertas nao contam como correcoes incorporadas.

O verificador nao baixa commits nem aplica patches. Usa os projetos do manifesto combinado, incluindo forks com o mesmo nome de repositorio. Instancias multiplas de um mesmo projeto sao conferidas individualmente. Projetos fora do manifesto ficam registrados fora do escopo; pastas declaradas ausentes, mudancas locais, objetos nao disponiveis e commits nao ancestrais impedem credito. Equivalencias por cherry-pick nao sao presumidas.

Reversoes padrao nao publicadas nos lotes sao rejeitadas. Reversoes publicadas como parte do proprio lote sao transicoes esperadas do upstream. O teste e de historico Git; nao comprova equivalencia funcional do codigo nem cobertura integral de CVEs, firmware ou kernel.

## Resultado na ROM

O overlay gerado fica em device/motorola/quark/overlay-security-generated/<variante>/, ignorado pelo Git. O mes nao e mais fixado em arquivo rastreado. Sem a verificacao (por exemplo, mka bacon direto), a configuracao padrao e Nao verificado.

Falha de rede ou consulta incompleta gera Nao verificado, sem reutilizar o mes de outra build. A compilacao prossegue; falha de gravacao que possa manter informacao antiga interrompe o script. Nao e usado cache de rede para declarar um mes verificado.

O relatorio fica em OUT_DIR/quark-security-backports.json (por exemplo out-user/quark-security-backports.json). Ele registra ramo, horario, lotes, commits, HEADs e pendencias. Ao concluir a build, o campo em Sobre o telefone > Versao do Android reflete o overlay gerado naquela execucao, sem alterar as datas oficiais Android/fabricante.

## Atualizar e compilar

```sh
cd ~/android/lineage18
git -C .repo/local_manifests pull --ff-only origin 'A11+KSU'
python3 .repo/local_manifests/concluir-sync-quark.py --branch 'A11+KSU' --apply
bash .repo/local_manifests/build-quark.sh
```

O helper sincroniza device, Settings e os outros projetos Quark gerenciados. O revert local em vendor/lineage nao e um desses projetos e nao e alterado pelo helper. Instalar a ROM completa; boot.img sozinho nao atualiza Settings.

## Validacao

Testes com repositorios Git temporarios cobrem ancestralidade, commit em outro ramo, revert local, revert publicado, lote anterior incompleto, alteracoes locais, falha de rede com mes antigo, paginacao, aliases de forks, fontes ausentes e separacao das versoes Android. As consultas reais aos catalogos 18.1 e 19.1 foram exercitadas. A compilacao completa e a tela devem ser validadas no Quark.

O fork de Settings precisa continuar incorporando futuras atualizacoes de seu upstream; a checagem nao realiza merges nem sincroniza fontes automaticamente.

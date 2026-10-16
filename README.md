# Proelium Studio

## Edição local sem API no Windows

Baixe **[Baixar Proelium Studio para Windows](https://github.com/emioccedilha-creator/proelium/raw/refs/heads/proelium-studio-download/downloads/Proelium-Studio-Windows.zip)**, extraia a pasta inteira e dê dois cliques em **ABRIR PROELIUM.cmd**. O navegador abre automaticamente. Não é necessário instalar Python, Node ou ComfyUI manualmente, criar uma chave nem montar workflows. O runtime e o motor de CPU são incluídos no ZIP. Mantenha a janela do iniciador aberta enquanto usa o aplicativo.

Na primeira abertura, o programa baixa automaticamente os três modelos públicos fixados em `desktop/model-catalog.json`: aproximadamente **5,3 GB** no total. O download pode ser retomado, verifica SHA-256 e não envia imagens do usuário. Depois da preparação, a edição funciona offline no computador. A interface mostra progresso e erros; não declara o motor pronto se faltar algum arquivo. Arquivos grandes são baixados em paralelo e gravados em fluxo, sem carregar o modelo inteiro na memória durante o download.

Requisitos do pacote: **Windows 10/11 x64, pelo menos 12 GB de RAM (16 GB ou mais recomendados), espaço para modelos e trabalhos, e internet no primeiro uso**. Não exige NVIDIA. Em CPU, a geração pode demorar bastante. Não foi medido o tempo no seu computador e nenhuma IA garante fidelidade perfeita ao cânone. O pacote não oferece execução Windows ARM.

1. Cadastre até dez imagens por personagem e os detalhes que devem ser preservados.
2. Importe a página e vincule os personagens relevantes.
3. Na Revisão, confira a instrução de correção já preenchida (ou ajuste o pedido) e clique em **Corrigir página agora**.
4. A página e todas as referências vinculadas são processadas pelo motor local; o resultado entra como versão pendente, preservando o original e o cânone.
5. Compare e aprove ou rejeite. Você não precisa levar a página ao Work Astra.

O modo CPU permite revisões com maior lado de 512, 768 ou 1024 px. Referências são fornecidas ao modelo em cópias de até 384 px para limitar RAM, mantendo as proporções. A resolução escolhida afeta o resultado; originais e referências completos continuam guardados. O limite desta integração é de trinta imagens vinculadas por edição; o programa recusa excedentes em vez de omitir referências.

### Dados e atualização do HTML anterior

O pacote abre em `http://127.0.0.1:8767`, endereço local fixo. Use o mesmo perfil do navegador e faça backups. Os dados do HTML anterior ficam em outra origem: abra o HTML antigo, exporte **Backup completo** e, no aplicativo novo, use **Restaurar backup portátil**. Não apague os dados antigos antes de conferir a restauração.

`engine-data/models` guarda pesos e `model-lock.json`. `engine-data/jobs` mantém cópias das entradas, prompt, relatório e resultado de cada edição. Modelos e trabalhos incompletos não entram no backup da biblioteca. Resultados concluídos importados na biblioteca entram normalmente no backup. Se a aba fechar, a revisão oferece **Recuperar edição anterior**; se todo o iniciador encerrar durante a geração, pode ser necessário solicitar novamente. O motor atende somente loopback e rejeita origens externas.

### Fontes e construção do pacote

- Motor nativo: stable-diffusion.cpp `master-969-8c442fb`, CPU, obtido da release oficial. O pacote contém os avisos de licença do projeto.
- Runtime portátil: Node.js 24.19.0 oficial, com licença incluída.
- Modelos: FLUX.2 klein 4B Q4_0 (leejet), Qwen3 4B Q4_K_M (unsloth), VAE FLUX.2 (Comfy-Org). As revisões e os checksums estão fixados no catálogo do projeto, sem necessidade de conta.

`tools/package_windows.py --archives <pasta>` constrói o ZIP após verificar os dois arquivos oficiais, com os checksums publicados pelos mantenedores. `tools/build_portable.py` recompõe o HTML. O servidor e o download usam somente módulos nativos do Node. Nenhum instalador altera o Python ou as configurações globais do computador.

### Verificação

**Resultado observado:** uma edição real em CPU/Linux com imagem sintética de 256×256 px e uma referência trocou o lenço vermelho pelo azul solicitado, mantendo a composição. A geração levou 236 segundos em quatro CPUs; esse tempo não é uma estimativa para páginas maiores ou dez referências. [Relatório e checksums](docs/native-validation.json), [original](docs/native-page.png), [referência](docs/native-reference.png) e [resultado real](docs/native-result.png). O pacote Windows tem seus binários oficiais conferidos, mas o iniciador Windows não foi executado neste ambiente Linux.


`node tests/engine.test.mjs` cobre seleção de arquivos, hash, retomada, falhas de download/RAM, todas as referências, resultado persistente, dimensões e proteção de origem. Defina `PROELIUM_NATIVE_PROBE` para acrescentar a inicialização do binário real ao teste. `tests/desktop_smoke.py` verifica o fluxo da interface e o retorno de revisão com executor simulado. `tools/validate_native.py --cache <pasta>` cria uma amostra sintética e executa uma edição real com os modelos baixados; requer Pillow somente na máquina de desenvolvimento.

O código do pacote é `desktop/server.mjs`, `desktop/engine.mjs`, `desktop/models.mjs` e `static/native.js`. Os conectores anteriores continuam como opções avançadas. Para desenvolvimento em Linux, aponte `PROELIUM_ENGINE_EXE` para o `sd-cli` oficial e `PROELIUM_ENGINE_DATA` para a pasta de cache e execute `node --use-env-proxy desktop/server.mjs --no-browser`. Não exponha esse servidor na rede.


## Biblioteca portátil em HTML (sem motor de IA)

Baixe **[Proelium Studio.html](dist/Proelium%20Studio.html)**, salve em uma pasta fixa e dê dois cliques. Abra com Edge ou Chrome atualizado. O arquivo já inclui a interface, o banco local e as funções de revisão: não precisa de Python, terminal, servidor, internet ou conta.

Os dados e imagens ficam no **IndexedDB do navegador**, não dentro do HTML. Use sempre o mesmo perfil e o mesmo caminho do arquivo, fora de janela anônima. Faça **Backup completo** regularmente: limpar dados do navegador, trocar de computador/perfil ou mover o HTML pode tornar o arquivo local indisponível. O botão **Restaurar backup portátil** recupera o ZIP completo, com confirmação antes de substituir dados existentes. O ZIP pode ser aberto normalmente pelo Explorador de Arquivos e contém JSON e imagens originais. Pacotes de revisão não são backups completos.

Backups portáteis e backups da versão Python são formatos diferentes e não são intercambiáveis nesta versão. Não mova ou descarte dados da versão anterior; exporte-os antes de trocar de versão.

A versão portátil foi testada no Chromium: cadastro, cânone protegido, imagens, revisão, decisões, persistência, exportação e restauração. O navegador gerenciado do ambiente de testes bloqueia URLs file://; o teste carregou o mesmo HTML por um servidor estático de teste, sem backend e sem requisições de rede da aplicação. A abertura por duplo clique no Windows não foi executada neste ambiente Linux.

### Para quem desenvolve

`python tools/build_portable.py` recompõe o arquivo único a partir de `static/` e `portable/storage.js`. `tests/portable_smoke.py` executa o fluxo portátil com Playwright; as dependências de testes são opcionais. O armazenamento portátil é separado do servidor e usa transações IndexedDB, arquivos Blob e ZIP padrão sem compressão. Conexões de rede são feitas somente quando você solicita teste ou edição no gerador opcional; a biblioteca funciona offline.

---

## Versão alternativa com servidor Python (opcional)

Aplicativo local em português brasileiro para memória visual e revisão manual do mangá Proelium. Funciona offline, sem API, assinatura ou modelo de IA. Python 3.10 ou superior; nenhuma dependência externa de execução.

## Executar no Windows

1. Instale Python pelo site oficial python.org, habilitando o Python Launcher.
2. Extraia ou clone este repositório em uma pasta sua.
3. Abra o PowerShell nessa pasta e execute:

```powershell
py -3 app.py
```

Abra `http://127.0.0.1:8765` no navegador do próprio computador. Mantenha o terminal aberto; Ctrl+C encerra. Para outra porta: `py -3 app.py --port 8767`. Em Linux/macOS use `python3 app.py`.

Não exponha o servidor na rede: é uma ferramenta pessoal, sem autenticação. Ele escuta apenas no endereço de loopback. As imagens são copiadas, não movidas, e permanecem em `data/files`; SQLite guarda registros e histórico em `data/studio.sqlite3`. Não apague essa pasta. Não há envio automático de dados para terceiros.

## Primeiro uso

O painel Início explica o fluxo. Cadastre personagens e referências em **Personagens** ou **Lugares e Objetos** (categorias Lugar, Objeto, Roupa e Referência visual). Adicione regras na **Bíblia Visual**. Um item aprovado fica imutável; para mudar o cânone, crie uma nova proposta. Aprovar uma proposta não modifica outros registros aprovados; coexistências e substituições devem ser descritas pelo autor.

Em **Páginas**, importe o original em PNG, JPEG ou WebP, até 25 MB por arquivo. Preencha capítulo/ordem, continuidade de entrada e saída, ligação com páginas próximas e referências relevantes. Em **Revisão**, selecione a página, baixe o pacote e copie o prompt. O ZIP contém os arquivos e contexto necessários; anexe-os manualmente ao Work Astra. Revise o pacote antes de compartilhar informações.

Transcreva os defeitos em registros com localização, gravidade, correção, origem e resolução. Use “Editar continuidade / importar versão” para acrescentar uma versão corrigida. Compare com o original, abra as imagens em tamanho integral e aprove ou rejeite com justificativa. Decisões posteriores ficam no Histórico, incluindo o estado anterior. A aprovação não resolve defeitos automaticamente. O original nunca é substituído e a revisão não altera a biblioteca canônica.

Não existe análise, detecção de defeitos ou edição automática nesta versão. Referências propostas também são incluídas quando explicitamente vinculadas e seu estado é identificado no prompt; somente regras aprovadas da Bíblia são incluídas. Continuidade é manual: vincule referências e descreva os estados e páginas relacionadas; não há inferência automática entre páginas.

## Backup, exportação e restauração

“Backup completo” baixa um ZIP com banco SQL consistente, exportação JSON e todos os arquivos. Guarde cópias em outro dispositivo; não há backup agendado. O pacote de revisão é uma exportação parcial, não substitui o backup completo.

Para restaurar um **backup confiável produzido pelo aplicativo**, encerre o servidor e escolha uma pasta nova/vazia. No PowerShell:

```powershell
$env:PROELIUM_DATA = "$PWD\dados-restaurados"
py -3 app.py --restore "C:\Backups\proelium-backup.zip"
py -3 app.py
```

A restauração recusa uma pasta com dados existentes. O backup contém SQL: não restaure arquivos de origem desconhecida. Para voltar à pasta padrão em outro terminal, execute sem definir PROELIUM_DATA. É possível também copiar toda a pasta `data` com o aplicativo encerrado. A restauração completa preserva arquivos e histórico; não existe importação/mesclagem de JSON nem exclusão de registros pela interface.

## Testes e arquitetura

```powershell
py -3 -m unittest discover -s tests -v
```

Os testes usam diretórios temporários: verificam proteção canônica, versões, decisões, prompt, ZIP, rejeição de entradas inválidas e restauração sem sobrescrita. `app.py` fornece servidor HTTP local, SQLite e armazenamento de arquivos. `static/` contém a interface sem dependências. `providers.py` define contratos separados para futuros provedores de visão (como Ollama) e edição. Não há provedor ativo ou chamada de rede de IA. A conexão futura deverá implementar esses contratos e um fluxo explícito de consentimento, mantendo o armazenamento e a revisão manual.

O servidor não implementa contas, colaboração simultânea nem sincronização. Não abra duas instâncias usando a mesma pasta de dados. Mantenha espaço suficiente para originais, revisões e ZIPs; backups são montados em memória. PDFs/CBZ devem ser convertidos em imagens antes da importação.

Teste opcional da interface em navegador (somente para desenvolvimento, não necessário para executar o programa):

```powershell
py -3 -m pip install playwright
py -3 -m playwright install chromium
py -3 tests/browser_smoke.py
```

Esse teste inicia e encerra seu próprio servidor e usa dados temporários separados. Pode-se apontar `CHROMIUM_PATH` para um Chromium já instalado. Na validação desta versão, os dois testes de dados/restauração e o fluxo completo no Chromium passaram. A execução no Windows está documentada; os testes desta entrega foram executados em Linux.


## Atualização 1.1: salvamento, dez imagens e edição conectada

Baixe novamente `dist/Proelium Studio.html` e substitua o HTML anterior **no mesmo local**, usando o mesmo navegador e perfil. Não limpe dados. Faça um backup antes de atualizar quando possível. O nome do banco IndexedDB foi mantido para preservar a biblioteca anterior. Uma prévia de arquivo dentro de um chat pode bloquear armazenamento; baixe o HTML e abra diretamente no Edge ou Chrome.

Ao salvar, o formulário mostra “Salvando…”, verifica a presença do registro no banco e abre a biblioteca de personagens. Erros aparecem dentro do formulário, mantendo os campos e arquivos selecionados. Removemos dependências de `crypto.randomUUID` e `structuredClone`; se SHA-256 não estiver disponível, a imagem ainda pode ser guardada com seu arquivo original, e os ZIPs continuam com verificação CRC. Falta de espaço ou bloqueio de banco não é apresentada como sucesso.

Cada personagem/referência aceita **até 10 imagens no total**, com prévias e contador. Use Ctrl para selecionar várias de uma vez; novas seleções substituem a seleção ainda não salva. Até 25 MB por imagem e 100 MB por envio pela interface. Itens aprovados continuam protegidos; cadastre uma proposta para alterar um cânone aprovado. Imagens de referência não equivalem a treinamento nem garantem que um modelo reconheça cada detalhe.

### Gerador de imagens

O botão **Corrigir página com gerador** envia diretamente o original, todas as imagens dos personagens vinculados, regras aprovadas, continuidade e instruções. A resposta é adicionada como nova revisão pendente; originais, cânone e decisões anteriores são mantidos. O pacote para Work Astra virou uma alternativa manual recolhível; não é exigido no fluxo conectado.

**Nenhum modelo ou serviço de IA está incluído.** Sem gerador local ou chave de uma API de edição, não há geração automática disponível. O gerador deste chat não é um serviço que o HTML possa acessar automaticamente. Não há instalação automática de modelos no computador do usuário.

- **ComfyUI local:** requer serviço em execução, modelo de edição compatível e workflow em formato API com os nós indicados na interface. Configure CORS no serviço para aceitar o navegador, mantendo o serviço vinculado ao endereço local; não exponha a porta publicamente. Os títulos `PROELIUM_PAGE`, `PROELIUM_REF_01` até o número necessário, `PROELIUM_PROMPT` e `PROELIUM_OUTPUT` mapeiam página, imagens, prompt e saída. Os LoadImage e o prompt devem estar conectados à saída. O número de slots de referência deve corresponder exatamente ao número de imagens vinculadas; não há descarte silencioso.
- **API de edição compatível:** exige endpoint HTTPS compatível com `/images/edits`, modelo e credencial própria, CORS e múltiplos campos `image[]`. O resultado deve conter `data[0].b64_json`. O provedor pode cobrar; o aplicativo pede confirmação antes do envio. Esse conector limita a 16 imagens no total (página + referências). A chave fica só na memória da aba e não é salva no backup nem no histórico. O aplicativo não tenta contornar restrições CORS de um provedor.

Configuração pública do gerador (URL, modelo, workflow) fica no navegador; backups da biblioteca não contêm essas preferências nem chaves. “Testar serviço” verifica a resposta do serviço, não a qualidade do modelo ou a execução do workflow. O workflow/modelo deve ser selecionado por quem administra o ComfyUI; o aplicativo não fornece um workflow universal, pois editores diferentes usam nós e modelos diferentes.

Teste opcional: `python tests/enhancements_smoke.py` (Playwright). Verifica dez imagens, limite e atomicidade, salvamento sem funções opcionais do navegador, erro de quota visível, gerador ausente e execução do conector ComfyUI contra um serviço **simulado**, com 11 uploads (página + 10 referências). Isso valida o conector e a preservação dos dados; **não valida a qualidade de uma edição por IA real**. Nenhum modelo de edição estava disponível nesta entrega.

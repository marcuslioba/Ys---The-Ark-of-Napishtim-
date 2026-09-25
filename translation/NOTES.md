# Ys: The Ark of Napishtim (PSP) — notas de tradução

## Status

### Concluído e funcional
- **Legendas de vídeo** (`data/movie/*.srt`, formato binário custom — ver `tools/srtbin.py`):
  as 2 cutscenes com fala (`im03a_kaizoku`, `im03b_kazaminooka`, 15 falas) foram
  traduzidas para português e reempacotadas em
  `output/Ys - The Ark of Napishtim (PT-BR).iso`.
  - Formato: `uint32 count` + N × (`uint32 start_ms`, `uint32 end_ms`,
    `char[20] speaker`, `uint32 text_len`, `char[text_len] text`).
  - Round-trip testado byte-a-byte contra os 11 arquivos `_eng.srt` originais: 100% ok.
  - **Testado visualmente no PPSSPP em 25/09/2026**: o ISO inicializa, passa pela
    tela de título, entra no menu, inicia "New Game" e reproduz a cutscene de
    abertura normalmente. Nenhum crash.
  - **Ainda não confirmado visualmente**: se os acentos "ã"/"õ" (usados na tradução)
    renderizam certo na fonte do jogo — precisa chegar na cena específica
    (pouco depois do início, quando a Arca aparece) para ver.

### Diálogo dos NPCs — formato decifrado, tradução de tamanho variável funcionando
- **Diálogo dos NPCs**: `data/arc/idm.bin` (2,5 MB, texto plano sem compressão).
  - Extraí e traduzi 3.692 das 3.786 falas em inglês identificadas (97,5%) usando
    detecção de idioma por palavras-função (`tools/lang_detect.py`) — os arquivos
    de tradução estão em `translated/batch_000.json` .. `batch_025.json`,
    consolidados em `extracted/translations_por.json`.
  - **Tentativa 1** (`tools/rebuild_idm.py`, tamanho variável ingênuo): atualizava
    o campo de tamanho de cada entrada sem entender a tabela de índice.
    Reempacotado em `output/Ys - The Ark of Napishtim (PT-BR) v2 QUEBRADO -
    NAO USAR.iso` — **TRAVA** ("Bad Execution Address") ao iniciar "New Game".
  - **Tentativa 2** (`tools/rebuild_idm_safe.py`, tamanho fixo): mantinha cada
    texto exatamente do mesmo tamanho do original (cortando/preenchendo com
    espaço). Não trava, mas corta ~4.800 das ~8.850 falas traduzidas no meio
    da palavra. Usado durante os testes de acentuação (ver seção de vídeo
    de fonte, abaixo). **Superado pela tentativa 3.**
  - **Tentativa 3 (ATUAL, tools/rebuild_idm_v2.py) — formato decifrado**:
    - O arquivo tem uma **tabela de índice** nos primeiros 0x3C00 bytes: 1446
      entradas de `(uint32 offset, uint32 size)`, little-endian, com `offset`
      relativo a `BASE=0x3C00` (onde os dados de texto começam). Bytes não
      usados da tabela são preenchidos com `0x38` ('8').
    - As 1446 entradas vêm em grupos consecutivos de 6: inglês, uma segunda
      variante de inglês ("UK"), francês, alemão, espanhol, italiano — sempre
      nessa ordem. Entradas vazias têm `size=0`.
    - Cada bloco não-vazio começa com um cabeçalho de 4 `uint32`
      (`msg_count, 1, 0, 0`), seguido de `msg_count` mensagens, cada uma:
      `uint32 msg_id, uint32 n_pages, uint32 n_tok`, depois `n_tok` valores
      `uint32` (códigos de formatação/página), depois `n_pages` strings
      (`uint32 len` + `len` bytes de texto).
    - Nada dentro de um bloco referencia outra posição do arquivo — só a
      tabela do início aponta pra cada bloco. Por isso a tentativa 1 travava:
      mudar o tamanho de um bloco sem atualizar essa tabela faz os blocos
      seguintes ficarem no lugar errado, e o jogo lê lixo como se fosse a
      contagem de mensagens/páginas seguinte.
    - `rebuild_idm_v2.py` faz o parse completo usando esse formato, troca o
      texto **sem limite de tamanho** (só nos slots 0 e 1 = inglês, evitando
      o bug de tradução vazar pra outros idiomas quando o texto original
      coincide), e recalcula a tabela de índice do zero com os novos
      offsets/tamanhos. Testado localmente: parse "round-trip" 100% ok,
      fim da tabela bate exatamente com o tamanho do arquivo, nenhuma
      tradução cortada. Arquivo cresce ~9KB (0,37%) em vez de manter o
      tamanho fixo.
    - **Ainda não testado no PPSSPP** — esse é o próximo passo. Risco residual
      conhecido: o jogo pode reservar um buffer de memória de tamanho fixo
      pra esse arquivo; um crescimento de 0,37% é pouco provável de estourar
      isso, mas só o teste no emulador confirma.
    - Descoberta lateral: o extrator antigo (`extract_idm.py`, heurístico)
      encontra 31.505 das 33.701 strings reais do arquivo — as ~2.196 que
      faltam são majoritariamente texto de ajuda/tutorial com símbolos de
      botão embutidos (bytes tipo `\x81\xa0`) que a heurística rejeita. Não
      afeta a tradução principal, mas significa que ainda existem falas
      (help/tutorial) nunca extraídas nem traduzidas.

### Não investigado
- `data/arc/help.bin` (texto de ajuda, multilíngue, não comprimido — mais fácil
  que idm.bin, já que é pequeno: 10KB) — não extraído/traduzido ainda.
- `data/menu/*` — texto de UI/menus (nomes de item, etc.) — provavelmente em
  outro arquivo `arc/*.bin` ou dentro do próprio `idm.bin`, não isolado.

## Ferramentas (`tools/`)
- `srtbin.py` — parse/build das legendas binárias de vídeo.
- `build_srt.py` — gera os `.srt` traduzidos a partir de `extracted/worksheet_por.json`.
- `repack_iso.py` — remonta o ISO trocando arquivos (usa `pycdlib`; o ISO é
  ISO9660 puro, sem Joliet/Rock Ridge/UDF, com nomes minúsculos não-conformes —
  o script desliga a validação de nome de arquivo do pycdlib para aceitar isso).
- `extract_idm.py` — extrator heurístico de texto do `idm.bin` (baseado em
  procurar dwords que parecem `text_len` seguidos de texto válido; rejeita
  qualquer candidato com byte nulo embutido — isso eliminou 100% do ruído de
  desalinhamento observado antes dessa correção).
- `lang_detect.py` — detector de idioma por contagem de palavras-função
  (en/fr/de/es/it), usado para isolar o inglês dentro do `idm.bin`
  (que mistura os 6 idiomas intercalados, sem blocos contíguos).
- `rebuild_idm.py` — reconstrói o `idm.bin` com o texto traduzido, atualizando
  o campo de tamanho de cada entrada. **Funciona estruturalmente, mas o
  resultado quebra o jogo — ver acima.**
- `scan_text.py` — varredura genérica de streams zlib em arquivos `arc/*.bin`
  (útil para achar texto solto em outros arquivos do jogo).

## Coisas úteis descobertas no caminho
- ISO montável direto via `Mount-DiskImage` do PowerShell (é ISO9660 puro).
- `data/arc/*.bin` (arquivos de cena, ex. `s_0000.bin`) empacotam malha 3D
  (`.xso`), lista de objetos (`.sob`), textura (formato proprietário
  `MIG.00.1PSP`, variante do GIM da Sony), animação (`.aia`), colisão
  (`.yco`), script de evento/label (`.sen`), câmera (`.scm`), e um script de
  elenco (`.sct`) — nenhum contém diálogo, são só assets visuais/de cena.
- Muitos arquivos usam compressão zlib com um cabeçalho custom de 8 bytes antes
  do stream (`data[8:]` é zlib puro, decodifica direto com `zlib.decompress`).
- `idm.bin` e `help.bin` são exceções: texto puro, sem compressão zlib.
- `idm.bin` mistura os 6 idiomas (eng/fra/ger/ita/spa/uki) intercalados sem
  blocos contíguos — não dá pra isolar por offset, só por conteúdo (ver
  `lang_detect.py`).
- Mapeamento de teclado padrão do PPSSPP (Windows) usado nos testes: START =
  Espaço, Cross/Confirmar (X) = Z, Círculo (O) = X, Quadrado = A, Triângulo = S.

## Como testar no PPSSPP
1. Montar/abrir o ISO em `output/`.
2. `Configurações do jogo > Mapeamento dos controles` confirma as teclas.
3. Espaço na tela de título → menu aparece.
4. Z em "New Game" → Z em "Normal" → se não travar, o jogo carrega a intro.

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

### Traduzido mas QUEBRADO — não usar
- **Diálogo dos NPCs**: `data/arc/idm.bin` (2,5 MB, texto plano sem compressão).
  - Extraí e traduzi 3.692 das 3.786 falas em inglês identificadas (97,5%) usando
    detecção de idioma por palavras-função (`tools/lang_detect.py`) — os arquivos
    de tradução estão em `translated/batch_000.json` .. `batch_025.json`,
    consolidados em `extracted/translations_por.json`.
  - Reconstruí o arquivo (`tools/rebuild_idm.py`) atualizando o campo de tamanho
    de cada entrada para o novo comprimento em bytes do texto traduzido —
    mesmo princípio do `srtbin.py`. A estrutura ficou íntegra (31.505 entradas,
    igual ao original, confirmado re-extraindo o arquivo reconstruído).
  - **Reempacotei em `output/Ys - The Ark of Napishtim (PT-BR) v2 QUEBRADO -
    NAO USAR.iso` e testei no PPSSPP: O JOGO TRAVA** ("Bad Execution Address" —
    a CPU pula para um endereço de memória inválido) assim que se tenta iniciar
    "New Game".
  - **Diagnóstico**: o `idm.bin` quase certamente tem uma tabela de índice/ponteiros
    em outro lugar do arquivo (ou no executável `EBOOT.BIN`) que aponta para a
    posição exata de cada trecho de texto. Alterar o tamanho de ~8.850 entradas
    sem entender essa tabela desloca todo o conteúdo seguinte, corrompendo
    qualquer ponteiro que apontava para depois do primeiro trecho editado.
  - **Isolei a causa**: testei o ISO SEM essa mudança (só legendas) e ele funciona
    perfeitamente — confirma que o problema é especificamente essa etapa.
  - **Para consertar**: seria preciso decifrar por completo o formato de
    cabeçalho de cada registro do `idm.bin` (os ~6-8 `uint32` antes do
    `text_len` — ver `extract_idm.py`), encontrar a tabela de índice que referencia
    esses offsets, e ou (a) manter cada texto traduzido no mesmo tamanho exato do
    original (via padding/truncamento, evitando qualquer realocação), ou
    (b) recalcular e reescrever todos os ponteiros afetados. A opção (a) é bem
    mais simples de implementar mas pode cortar traduções mais longas que o inglês.

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

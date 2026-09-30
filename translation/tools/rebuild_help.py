"""Rebuild data/arc/help.bin (in-game Controls/Help screen) in PT-BR.

Format (5 language blocks: ENG, FRA, GER, SPA, ITA -- no UKI):
    uint32 LE x5   absolute offset of each block, in that order
    each block:
        uint32 LE  text length
        char[len]  text ('#' = newline, '##' = paragraph break,
                          '@1'-'@4' = button-icon glyphs, kept as-is)

Only the ENG block is replaced with the PT-BR translation. FRA/GER/
SPA/ITA are copied byte-for-byte from the original, just relocated,
since the new ENG block is a different length. The 5 header offsets
are recomputed accordingly.
"""
import struct
from pathlib import Path

root = Path(__file__).parent.parent
data = (root / 'extracted' / 'arc' / 'help.bin').read_bytes()

offsets = struct.unpack_from('<5I', data, 0)

# Slice out each original block's raw bytes (length prefix + text).
blocks = []
for i, off in enumerate(offsets):
    end = offsets[i + 1] if i + 1 < len(offsets) else len(data)
    blocks.append(data[off:end])

pt_text = (
    "Controles Basicos##"
    "Ataque usando o botao @4.#"
    "Aperte @4 repetidamente para um combo de 3 golpes.##"
    "Pule usando o botao @2.#"
    "Use os botoes direcionais para#"
    "mudar de direcao.##"
    "Aperte o botao @3 para usar itens equipados.##"
    "Ataques Especiais##"
    "Golpe pra Cima: Pule e ataque a cabeca.#"
    "Aperte @4 enquanto sobe no pulo.##"
    "Golpe pra Baixo: Pule e ataque os pes.#"
    "Aperte @4 enquanto desce#"
    "do pulo.##"
    "Investida: Avance e ataque.#"
    "Toque um direcional, depois @4.##"
    "Pulo de Investida: Permite pulos longos.#"
    "Avance, pule, depois aperte @2.##"
    "Habilidades da Espada##"
    "Habilidade da Espada: Ataque depende da espada.#"
    "Habilidade da Espada do Vento: Aperte @4 logo#"
    "apos o combo de 3 golpes para um golpe extra.##"
    "Habilidade da Espada do Fogo: Aumenta o ATK.#"
    "Segure o botao @4.##"
    "Habilidade da Espada do Trovao: Aperte @4#"
    "repetidamente para atravessar o inimigo.##"
    "Magia da Espada##"
    "Ative a magia apertando o botao @1.##"
    "A magia consome MP quando usada.#"
    "Cada espada tem efeitos unicos.##"
    "O medidor de MP aumenta se voce atacar#"
    "um inimigo ou sofrer dano.###"
    "Equipamento##"
    "Abra o menu com START e selecione#"
    "'EQUIP'para entrar na Tela de Equipamento. ##"
    "Selecione armas e itens apropriados.##"
    "WEAPON: A espada equipada.#"
    "Use L e R para trocar de espada.##"
    "Shield: O escudo equipado.##"
    "Armor: A armadura equipada.##"
    "Accessory: O acessorio equipado.##"
    "Item: O item consumivel equipado.#"
    "Itens equipados podem ser usados durante#"
    "o jogo apertando o botao @3.##"
    "Efeitos Anormais##"
    "Voce pode se recuperar usando itens#"
    "ou encontrando pontos de save.#"
    "Efeitos anormais desaparecem apos um#"
    "tempo, exceto 'Maldicao'.##"
    "Veneno: Diminui o HP aos poucos#"
    "mas nunca deixa o HP chegar a 0.##"
    "Lentidao: Move mais devagar. Nao pula tao alto.##"
    "Confusao: Move na direcao oposta.##"
    "Maldicao: Diminui DEF e ATK.#"
    "Nao passa com o tempo.#"
)

pt_bytes = pt_text.encode('latin-1')
new_eng_block = struct.pack('<I', len(pt_bytes)) + pt_bytes
blocks[0] = new_eng_block

new_offsets = []
cursor = 20  # 5 x uint32 header
for b in blocks:
    new_offsets.append(cursor)
    cursor += len(b)

out = struct.pack('<5I', *new_offsets) + b''.join(blocks)

out_path = root / 'output' / 'help.bin'
out_path.write_bytes(out)
print(f'original size {len(data)}, new size {len(out)}')
print('new offsets:', [hex(o) for o in new_offsets])

# Analisador Léxico e Sintático — Linguagem Elgol

Analisador para a linguagem **Elgol**, feito em **Python 3** com
**PLY (Python Lex-Yacc)**:

- **Parte 1 — análise léxica** (`ply.lex`): reconhece os tokens, monta a
  tabela de símbolos e relata erros léxicos.
- **Parte 2 — análise sintática** (`ply.yacc`): verifica se a sequência de
  tokens segue a gramática do Elgol, gera a árvore sintática e relata erros
  sintáticos com linha e tokens esperados, recuperando-se para encontrar
  vários erros no mesmo arquivo.

Documentação das regras:

- [`regras_lexicas`](regras_lexicas) — tokens, expressões regulares e tratamento de erro léxico
- [`regras_sintaticas.md`](regras_sintaticas.md) — gramática BNF, precedência e tratamento de erro sintático
- [`docs/artigo_parte2.md`](docs/artigo_parte2.md) — texto da seção da Parte 2 para o artigo

---

## Instalação

Requer Python 3.8+.

```bash
pip install -r requirements.txt
```

(instala `ply` e `pytest`)

## Como usar

```bash
cd elgol
python3 main.py tests/correto.elgol
python3 main.py tests/exemplos/professor/exemplo3.elgol
```

Saída: lista de tokens, tabela de símbolos, erros léxicos, erros sintáticos e,
se o programa for válido, a árvore sintática. Código de saída `0` para
programa válido e `1` se houver qualquer erro.

Opções:

| Opção | Efeito |
|---|---|
| `--sem-tokens` | não imprime a lista de tokens |
| `--sem-arvore` | não imprime a árvore sintática |

Exemplo de erro:

```
=== ERROS SINTATICOS ===
linha 25: token inesperado identificador = 'Variavel'; esperado: 'senao'

RESULTADO: programa INVÁLIDO
```

## Demonstração

```bash
cd elgol
python3 demo.py            # roda todos os exemplos e mostra o resumo
python3 demo.py -v         # mostra cada erro encontrado nos exemplos incorretos
python3 demo.py --arvore   # mostra a árvore dos exemplos corretos
```

## Testes automatizados

```bash
cd elgol
python3 -m pytest -v tests
```

83 testes: os 5 exemplos da Definição do Projeto (Parte 2), os exemplos
corretos (devem ser aceitos) e incorretos (devem ser rejeitados **na linha
esperada**), erros léxicos, formato da árvore (sem precedência: da esquerda
para a direita), todos os operadores relacionais, `para`, funções, `elgio` e
recuperação de erros.

---

## Estrutura do projeto

```
elgol/
├── main.py                 # linha de comando
├── analyzer.py             # junta léxico + sintático (função analyze)
├── demo.py                 # roteiro de demonstração
├── lexer/
│   ├── lexer.py            # Parte 1: regras léxicas (ply.lex)
│   └── token.py            # enum com os tipos de token
├── symbols/
│   └── symbols_table.py    # tabela de símbolos
├── syntax/
│   ├── parser.py           # Parte 2: gramática (ply.yacc)
│   └── ast.py              # nós da árvore sintática
└── tests/
    ├── correto.elgol       # exemplo da Parte 1
    ├── incorreto.elgol     # exemplo com erros léxicos da Parte 1
    ├── exemplos/
    │   ├── professor/      # exemplos 1 a 5 da Definição do Projeto
    │   ├── corretos/       # programas válidos
    │   └── incorretos/     # um erro sintático típico por arquivo
    └── test_analisador.py  # testes pytest
```

## Resumo da linguagem

```
* comentário até o fim da linha
DECIMAL $Soma (DECIMAL Numm, DECIMAL Dois) .
inicio .
    elgio = Numm + Dois .
fim .

inicio .
    DECIMAL Teste .
    Teste = 45 x $Soma(30, 40) .
    se Teste maior _Z_ .
    entao .
    inicio .
        Teste = Teste - 1 .
    fim .
    senao .
    inicio .
    fim .
    enquanto Teste menor 100 .
    inicio .
        Teste = Teste + 1 .
    fim .
    para Contar Teste .
    inicio .
    fim .
fim .
```

- Um comando por linha, sempre terminado com `.` (inclusive `inicio.`, `fim.`, `entao.`, `senao.`).
- Expressões **sem precedência** (da esquerda para a direita); parênteses só em chamada de função.
- Identificadores: consoante maiúscula no início, minúscula no fim, só letras, ≥ 4 caracteres.
- Funções: `$` + identificador. Números: inteiros sem zero à esquerda (o zero é `_Z_`).
- Operadores: `+ - x / RESTO EXP`, `_NEG_`; relacionais `maior menor igual diferente migual MIgual`.

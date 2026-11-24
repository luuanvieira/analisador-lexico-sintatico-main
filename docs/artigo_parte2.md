# Texto para o artigo — Parte 2: Análise Sintática

> Seções para acrescentar ao artigo do TR4 (depois das seções da análise
> léxica). Ajuste a numeração das seções e figuras ao artigo de vocês.

---

## X. Análise Sintática

### X.1 Fundamentação

A análise sintática é a segunda fase de um compilador. Ela recebe a sequência
de tokens produzida pelo analisador léxico e verifica se essa sequência pode
ser gerada pela gramática da linguagem, que é uma **gramática livre de
contexto** (GLC). Enquanto o analisador léxico decide se cada palavra do
programa é válida (por exemplo, se `Contador` é um identificador bem formado),
o analisador sintático decide se as palavras estão **na ordem correta** (por
exemplo, se toda atribuição tem a forma `identificador = expressão.`).

O resultado da análise é uma **árvore sintática**, que representa a estrutura
hierárquica do programa e serve de entrada para as fases seguintes
(análise semântica e geração de código). Quando a sequência não pertence à
linguagem, o analisador deve relatar o erro com a sua localização e, de
preferência, continuar a análise para encontrar outros erros (Aho et al.,
2008).

Os analisadores sintáticos dividem-se em **descendentes** (*top-down*, como
os LL(1) e os descendentes recursivos), que constroem a árvore da raiz para
as folhas, e **ascendentes** (*bottom-up*, como os LR, SLR e LALR), que partem
dos tokens e aplicam reduções até chegar ao símbolo inicial. Os analisadores
ascendentes aceitam uma classe maior de gramáticas, incluindo gramáticas
recursivas à esquerda, o que permite escrever as expressões aritméticas de
forma natural.

### X.2 Ferramenta: `ply.yacc`

Mantendo a escolha do TR4, a análise sintática foi feita com o módulo
`ply.yacc` da biblioteca **PLY (Python Lex-Yacc)** (Beazley, 2001–2025),
que reproduz em Python a ferramenta clássica *yacc*. O PLY gera um analisador
**LALR(1)**: a partir das regras da gramática ele constrói automaticamente as
tabelas de ação (*shift*, *reduce*, aceitar, erro) e de desvio (*goto*) do
autômato de pilha.

Cada regra é escrita como uma função Python. A produção em notação BNF fica
na *docstring* da função e o corpo da função monta o nó correspondente da
árvore. Por exemplo, a regra da atribuição:

```python
def p_atribuicao(p):
    "atribuicao : ID ASSIGN expressao DOT"
    p[0] = Node("atribuicao", [Node("id", value=p[1]), p[3]])
```

Uma vantagem prática do PLY é que o analisador léxico e o sintático
compartilham a mesma lista de tokens: o parser importa a tupla `tokens` do
módulo léxico da Parte 1, que só recebeu dois ajustes pequenos (aceitar a
grafia `Migual` e relatar palavras acentuadas como um único erro). Além disso, o PLY
detecta e relata conflitos na gramática no momento em que as tabelas são
geradas, o que ajudou a validar as regras durante o desenvolvimento.

### X.3 Gramática do Elgol

A gramática implementada é apresentada no Quadro X (copiar a BNF do arquivo
`regras_sintaticas.md`). As principais decisões foram:

- **Estrutura do programa**: zero ou mais definições de função seguidas do
  programa principal, delimitado por `inicio .` e `fim .`.
- **Um comando por linha, sempre terminado com `.`**, inclusive as palavras
  solitárias `inicio`, `fim`, `entao` e `senao`.
- **Funções** são definidas por `DECIMAL $Nome (DECIMAL Param, ...) .`
  seguido de um bloco. O resultado é indicado pela palavra reservada `elgio`,
  que tem uma regra de expressão própria sem chamada de função como operando.
- **Comandos de controle**: `enquanto condição .`, `para Contador limite .` e
  `se condição .` / `entao .` / bloco / `senao .` / bloco — o `senao` é
  obrigatório, mesmo vazio.
- **Expressões lógicas** têm exatamente dois operandos (identificador, número
  ou `_Z_`) e um dos operadores relacionais (`maior`, `menor`, `igual`,
  `diferente`, `migual`, `MIgual`).
- **Chamadas de função** só aceitam identificadores, números ou `_Z_` como
  argumentos; uma função pode ser operando de uma expressão, mas nunca alvo
  da atribuição.

**Ausência de precedência.** O Elgol não impõe precedência de operadores: a
expressão é avaliada da esquerda para a direita e os parênteses existem
apenas para os parâmetros de função. Por isso a gramática **não usa** a
tabela `precedence` do PLY; a regra de expressão é recursiva à esquerda e
cada operando é simples:

```
expressao ::= expressao operador operando | operando
```

Com isso `Bare + Breca x 45` gera a árvore `((Bare + Breca) x 45)`. Essa
forma é naturalmente não ambígua, e a gramática final não possui nenhum
conflito *shift/reduce* ou *reduce/reduce*.

### X.4 Tratamento de erros sintáticos

Quando o autômato encontra um token para o qual não há ação na tabela, o PLY
chama a função `p_error`. Nela o analisador registra:

1. a **linha** do token;
2. o **token encontrado** e seu valor;
3. quando a lista é pequena, os **tokens esperados** naquele ponto,
   obtidos da própria tabela de ações do estado em que ocorreu o erro.

Exemplo de saída para um `se` sem `senao`:

```
linha 25: token inesperado identificador = 'Variavel'; esperado: 'senao'
```

A regra "um comando por linha, terminado em `.`" é verificada sobre a lista
de tokens, usando apenas o número de linha de cada token: o último token de
cada linha deve ser `.`, e o `.` deve ser o último da linha. Assim a falta de
`.` é apontada na própria linha em que ocorreu; um `.` virtual é inserido
para que o parser continue sem erros em cascata.

Para não parar no primeiro erro, foi usada a **recuperação em modo pânico**
do yacc, com produções como `comando : error DOT`: ao encontrar um erro, o
parser descarta tokens até o próximo `.` e continua a análise. Variações
dessa produção também consomem o bloco de um `enquanto`/`para`/`se` cuja
primeira linha tinha erro. Dessa forma um mesmo arquivo relata vários erros
independentes.

### X.5 Árvore sintática

Para programas válidos, o analisador imprime a árvore sintática. Por
exemplo, para o trecho

```
se Nota maior 6.
entao.
inicio.
    Situacao = 1.
fim.
senao.
inicio.
fim.
```

é gerada a árvore:

```
se
├── condicao (maior)
│   ├── id (Nota)
│   └── numero (6)
├── entao
│   └── atribuicao
│       ├── id (Situacao)
│       └── numero (1)
└── senao
```

### X.6 Testes e resultados

Os testes usam os cinco exemplos da Definição do Projeto, além de programas
próprios: 6 corretos e 22 incorretos, cada um com um erro típico (falta de
`.`, bloco sem `fim`, falta de `entao` ou de `senao`, `senao` sem `se`, falta de `inicio`, atribuição a um número, operador sem operando, operador
matemático ou função na expressão lógica, três operandos, função no `elgio`,
função como parâmetro, função como alvo, parênteses na expressão, dois
comandos na mesma linha, comparação numa atribuição, `para` sem limite,
vários erros e mistura de erros léxicos e sintáticos).

A verificação foi automatizada com o **pytest** em 83 casos de teste, que
conferem: (a) que os programas corretos são aceitos; (b) que cada programa
incorreto é rejeitado na linha esperada; (c) que nos exemplos do professor
os erros são apontados nas linhas indicadas na especificação — por exemplo,
no Exemplo 3 são relatados erros nas linhas 2, 3, 6, 7, 11, 21 e 25; (d) o
formato da árvore, comprovando a avaliação da esquerda para a direita; e (e)
os operadores relacionais, o `para`, as funções e a recuperação após erros.

| Conjunto | Arquivos | Resultado esperado | Resultado obtido |
|---|---|---|---|
| Exemplos do professor | 5 | 1 aceito, 4 rejeitados | (preencher) |
| Corretos | 6 | aceitos | (preencher) |
| Incorretos | 22 | rejeitados na linha esperada | (preencher) |
| Testes pytest | 83 | aprovados | (preencher) |

### X.7 Limitações

A análise sintática garante apenas a **forma** do programa. Verificações que
dependem de significado — como usar uma variável antes de atribuir um valor a
ela, ou chamar uma função com o número errado de argumentos — pertencem à
análise semântica e não foram tratadas nesta etapa. A tabela de símbolos
construída na Parte 1 já registra os identificadores e as linhas em que
aparecem, e pode ser usada como base para essa próxima fase.

---

## Referências (acrescentar às do artigo)

AHO, A. V.; LAM, M. S.; SETHI, R.; ULLMAN, J. D. **Compiladores: princípios,
técnicas e ferramentas**. 2. ed. São Paulo: Pearson Addison-Wesley, 2008.

BEAZLEY, D. M. **PLY (Python Lex-Yacc)**. Disponível em:
<https://www.dabeaz.com/ply/>. Acesso em: nov. 2026.

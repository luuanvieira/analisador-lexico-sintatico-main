# Regras Sintáticas — Analisador do Elgol

## 1. Ferramenta

A análise sintática usa o módulo **`ply.yacc`** do PLY (o mesmo pacote da
análise léxica). O PLY gera um analisador **LALR(1)** ascendente
(*shift-reduce*): cada regra da gramática é escrita como uma função Python
cuja *docstring* contém a produção em BNF, e o corpo da função monta o nó
correspondente da árvore sintática.

Os tokens consumidos pelo parser são exatamente os produzidos pelo
analisador léxico da Parte 1 (`elgol/lexer/lexer.py`). O parser nunca olha o
código-fonte: ele vê apenas o tipo de cada token (`ID`, `NUMBER`, `MAIOR`...)
e o número da linha.

A gramática abaixo **não tem conflitos** shift/reduce nem reduce/reduce e
**não usa tabela de precedência**.

---

## 2. Gramática (BNF)

Terminais em MAIÚSCULAS (nome do token) ou entre aspas (lexema).

```
programa          ::= funcoes bloco

funcoes           ::= funcoes funcao
                    | ε

bloco             ::= 'inicio' '.' comandos 'fim' '.'

funcao            ::= 'DECIMAL' FUNCID '(' parametros ')' '.' bloco

parametros        ::= lista_parametros | ε
lista_parametros  ::= parametro | lista_parametros ',' parametro
parametro         ::= 'DECIMAL' ID

comandos          ::= comandos comando
                    | ε

comando           ::= declaracao
                    | atribuicao
                    | retorno
                    | negacao
                    | condicional
                    | repeticao_enquanto
                    | repeticao_para

declaracao        ::= 'DECIMAL' ID '.'
atribuicao        ::= ID '=' expressao '.'
retorno           ::= 'elgio' '=' expressao_elgio '.'
negacao           ::= '_NEG_' ID '.'

condicional       ::= 'se' condicao '.'
                      'entao' '.' bloco
                      'senao' '.' bloco
repeticao_enquanto ::= 'enquanto' condicao '.' bloco
repeticao_para    ::= 'para' ID limite '.' bloco
limite            ::= ID | NUMBER | '_Z_'

condicao          ::= valor relacional valor
relacional        ::= 'maior' | 'menor' | 'igual' | 'diferente'
                    | 'migual' | 'MIgual'

expressao         ::= expressao operador operando | operando
expressao_elgio   ::= expressao_elgio operador operando_simples | operando_simples
operador          ::= '+' | '-' | 'x' | '/' | 'EXP' | 'RESTO'

operando          ::= operando_simples | chamada | '_NEG_' chamada
operando_simples  ::= valor | '_NEG_' valor
valor             ::= ID | NUMBER | '_Z_'

chamada           ::= FUNCID '(' argumentos ')'
argumentos        ::= lista_argumentos | ε
lista_argumentos  ::= valor | lista_argumentos ',' valor
```

Produções de recuperação de erro (só usadas quando há erro):

```
funcao  ::= 'DECIMAL' error '.' bloco
comando ::= error '.'
          | error '.' bloco
          | error '.' 'entao' '.' bloco 'senao' '.' bloco
```

---

## 3. Regras em linguagem natural

1. O programa é uma sequência (opcional) de **definições de função** seguida
   do **programa principal** `inicio . ... fim .`.
2. **Sempre um único comando por linha, sempre terminando com `.`**. As
   palavras solitárias `inicio`, `fim`, `entao` e `senao` também são
   seguidas de `.`.
3. **Expressão matemática**: um `ID` recebe (`=`) uma sequência de operandos
   separados por operadores. Não há limite de operadores.
4. **Sem precedência**: a expressão é agrupada da esquerda para a direita.
   `Bare + Breca x 45` é `(Bare + Breca) x 45`. A gramática é recursiva à
   esquerda e não usa a tabela `precedence` do PLY.
5. **Parênteses** só existem na chamada de função, nunca para agrupar.
6. **Função não pode ser alvo** de uma expressão (`$Soma = 10.` é erro), mas
   pode ser operando (`Teste = 45 x $Soma(30, 40).`).
7. **Argumentos de função** só podem ser `ID`, número ou `_Z_` — função não
   pode ser parâmetro de outra função.
8. **Definição de função**: `DECIMAL $Nome (DECIMAL Param, ...) .` seguida de
   um bloco `inicio . ... fim .`. Os parâmetros são sempre `DECIMAL ID`.
9. **`elgio`** funciona como uma expressão matemática, mas **não aceita
   chamada de função** como operando (há uma regra própria,
   `expressao_elgio`, sem `chamada`).
10. **Expressão lógica** (`se`, `enquanto`): exatamente **dois operandos**
    (`ID`, número ou `_Z_`) com um operador relacional entre eles. Não aceita
    operadores matemáticos nem funções.
11. **`enquanto`**: `enquanto condição .` seguido de um bloco.
12. **`para`**: `para Contador limite .` seguido de um bloco; o contador é
    um `ID` e o limite é número ou `ID`.
13. **`se`**: `se condição .` / `entao .` / bloco / `senao .` / bloco. O
    **`senao` é obrigatório**, mesmo vazio (`inicio .` `fim .`).
14. `_NEG_ ID .` é aceito como comando (exemplo da especificação) e `_NEG_`
    também pode preceder um operando dentro da expressão.

---

## 4. Tratamento de erros sintáticos

- Cada erro é registrado com a **linha**, o **token inesperado** e, quando
  a lista é curta, os **tokens que eram esperados** naquele ponto (lidos da
  tabela de ações LALR do estado em que o erro ocorreu). Exemplo:

  ```
  linha 8: token inesperado identificador = 'Valor'; esperado: 'senao'
  ```

- **Regra de linhas.** Antes do parser, a lista de tokens é verificada
  usando apenas o número de linha de cada token: o último token de cada
  linha tem que ser `.` e o `.` tem que ser o último token da linha. Assim o
  erro de "faltou `.`" é apontado **na própria linha** (e não na seguinte).
  Quando falta o `.`, um `.` virtual é inserido para que a análise continue
  sem erros em cascata.
- **Recuperação em modo pânico**: as produções com `error` fazem o parser
  descartar tokens até o próximo `.` e continuar. Assim um único arquivo pode
  relatar vários erros (ver `tests/exemplos/professor/exemplo3.elgol`).
- Se o arquivo termina antes de fechar todos os blocos, o erro é
  `fim de arquivo inesperado (faltou 'fim.'?)`.
- Tokens descartados pelo analisador léxico (por serem inválidos) não chegam
  ao parser; por isso um erro léxico pode gerar também um erro sintático na
  mesma linha.

---

## 5. Fora do escopo (erros semânticos)

Conforme a especificação, não são verificados: variável ou função não
declarada, recursividade, função sem atribuição a `elgio` e uso de `elgio`
fora de uma função.

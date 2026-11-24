"""Parte 2 — analisador sintático do Elgol (ply.yacc, LALR(1)).

A gramática segue a "Definição do Projeto — Parte 2":

* o programa é uma sequência (opcional) de definições de função seguida do
  bloco principal ``inicio . ... fim .``;
* todo comando termina com ``.`` e fica sozinho na sua linha
  (``inicio``, ``fim``, ``entao`` e ``senao`` também são seguidos de ``.``);
* expressões matemáticas NÃO têm precedência: são avaliadas da esquerda para
  a direita, e parênteses só aparecem na chamada de função;
* expressões lógicas (``se`` / ``enquanto``) têm exatamente dois operandos
  (id, número ou ``_Z_``) e um operador relacional;
* ``elgio = ...`` é uma expressão matemática que não aceita chamada de função;
* argumentos de chamada de função só podem ser id, número ou ``_Z_``.
"""
import ply.lex as lex
import ply.yacc as yacc

from lexer.lexer import tokens  # noqa: F401  (o PLY lê a lista de tokens deste módulo)
from syntax.ast import Node

TOKEN_DESCRIPTIONS = {
    "ID": "identificador",
    "FUNCID": "nome de função",
    "NUMBER": "número",
    "ASSIGN": "'='",
    "PLUS": "'+'",
    "MINUS": "'-'",
    "DIV": "'/'",
    "MULT": "'x'",
    "DOT": "'.'",
    "LPAREN": "'('",
    "RPAREN": "')'",
    "COMMA": "','",
    "ELGIO": "'elgio'",
    "DECIMAL": "'DECIMAL'",
    "Z": "'_Z_'",
    "NEG": "'_NEG_'",
    "EXP": "'EXP'",
    "RESTO": "'RESTO'",
    "ENQUANTO": "'enquanto'",
    "SE": "'se'",
    "ENTAO": "'entao'",
    "SENAO": "'senao'",
    "PARA": "'para'",
    "INICIO": "'inicio'",
    "FIM": "'fim'",
    "MAIOR": "'maior'",
    "MENOR": "'menor'",
    "IGUAL": "'igual'",
    "DIFERENTE": "'diferente'",
    "MIGUAL": "'migual'",
    "MIGUAL_CAP": "'MIgual'",
    "$end": "fim do arquivo",
}

# Sem tabela de precedência: o Elgol não impõe precedência de operadores.
syntax_errors = []
start = "programa"


# ================================================================ programa

def p_programa(p):
    "programa : funcoes bloco_principal"
    p[0] = Node("programa", p[1] + [p[2]], lineno=p.lineno(2))


def p_funcoes_lista(p):
    "funcoes : funcoes funcao"
    p[0] = p[1] + [p[2]]


def p_funcoes_vazio(p):
    "funcoes : "
    p[0] = []


def p_bloco_principal(p):
    "bloco_principal : bloco"
    p[0] = Node("principal", p[1].children)


def p_bloco(p):
    "bloco : INICIO DOT comandos FIM DOT"
    p[0] = Node("bloco", p[3], lineno=p.lineno(1))


# ================================================================ funções

def p_funcao(p):
    "funcao : DECIMAL FUNCID LPAREN parametros RPAREN DOT bloco"
    p[0] = Node("funcao", [Node("parametros", p[4]), p[7]], value=p[2], lineno=p.lineno(1))


def p_funcao_erro(p):
    "funcao : DECIMAL error DOT bloco"
    p[0] = Node("erro", lineno=p.lineno(1))


def p_parametros(p):
    """parametros : lista_parametros
                  | """
    p[0] = p[1] if len(p) > 1 else []


def p_lista_parametros_um(p):
    "lista_parametros : parametro"
    p[0] = [p[1]]


def p_lista_parametros_varios(p):
    "lista_parametros : lista_parametros COMMA parametro"
    p[0] = p[1] + [p[3]]


def p_parametro(p):
    "parametro : DECIMAL ID"
    p[0] = Node("parametro", value=p[2])


# ================================================================ comandos

def p_comandos_lista(p):
    "comandos : comandos comando"
    p[0] = p[1] + [p[2]]


def p_comandos_vazio(p):
    "comandos : "
    p[0] = []


def p_comando(p):
    """comando : declaracao
               | atribuicao
               | retorno
               | negacao
               | condicional
               | repeticao_enquanto
               | repeticao_para"""
    p[0] = p[1]


def p_comando_erro(p):
    """comando : error DOT
               | error DOT bloco
               | error DOT ENTAO DOT bloco SENAO DOT bloco"""
    # Recuperação em modo pânico: descarta tokens até o próximo '.'.
    # As duas últimas formas também consomem o bloco de um enquanto/para/se
    # cuja primeira linha tinha erro, evitando erros em cascata no 'fim.'.
    p[0] = Node("erro", lineno=p.lineno(2))


def p_declaracao(p):
    "declaracao : DECIMAL ID DOT"
    p[0] = Node("declaracao", [Node("id", value=p[2])], value="DECIMAL", lineno=p.lineno(1))


def p_atribuicao(p):
    "atribuicao : ID ASSIGN expressao DOT"
    p[0] = Node("atribuicao", [Node("id", value=p[1]), p[3]], lineno=p.lineno(1))


def p_retorno(p):
    "retorno : ELGIO ASSIGN expressao_elgio DOT"
    p[0] = Node("elgio", [p[3]], lineno=p.lineno(1))


def p_negacao(p):
    "negacao : NEG ID DOT"
    p[0] = Node("negativo", [Node("id", value=p[2])], value="_NEG_", lineno=p.lineno(1))


def p_condicional(p):
    "condicional : SE condicao DOT ENTAO DOT bloco SENAO DOT bloco"
    p[0] = Node("se", [p[2], Node("entao", p[6].children), Node("senao", p[9].children)],
                lineno=p.lineno(1))


def p_repeticao_enquanto(p):
    "repeticao_enquanto : ENQUANTO condicao DOT bloco"
    p[0] = Node("enquanto", [p[2], Node("corpo", p[4].children)], lineno=p.lineno(1))


def p_repeticao_para(p):
    "repeticao_para : PARA ID limite DOT bloco"
    p[0] = Node("para", [Node("contador", value=p[2]), p[3], Node("corpo", p[5].children)],
                lineno=p.lineno(1))


def p_limite(p):
    """limite : ID
              | NUMBER
              | Z"""
    p[0] = Node("limite", value=p[1])


# ================================================================ expressão lógica

def p_condicao(p):
    "condicao : valor relacional valor"
    p[0] = Node("condicao", [p[1], p[3]], value=p[2])


def p_relacional(p):
    """relacional : MAIOR
                  | MENOR
                  | IGUAL
                  | DIFERENTE
                  | MIGUAL
                  | MIGUAL_CAP"""
    p[0] = p[1]


# ================================================================ expressão matemática
# Recursão à esquerda sem precedência: "A + B x C" vira ((A + B) x C).

def p_expressao_binaria(p):
    "expressao : expressao operador operando"
    p[0] = Node("operacao", [p[1], p[3]], value=p[2])


def p_expressao_operando(p):
    "expressao : operando"
    p[0] = p[1]


def p_expressao_elgio_binaria(p):
    "expressao_elgio : expressao_elgio operador operando_simples"
    p[0] = Node("operacao", [p[1], p[3]], value=p[2])


def p_expressao_elgio_operando(p):
    "expressao_elgio : operando_simples"
    p[0] = p[1]


def p_operador(p):
    """operador : PLUS
                | MINUS
                | MULT
                | DIV
                | EXP
                | RESTO"""
    p[0] = p[1]


def p_operando(p):
    "operando : operando_simples"
    p[0] = p[1]


def p_operando_chamada(p):
    "operando : chamada"
    p[0] = p[1]


def p_operando_neg_chamada(p):
    "operando : NEG chamada"
    p[0] = Node("negativo", [p[2]], value="_NEG_")


def p_operando_simples(p):
    "operando_simples : valor"
    p[0] = p[1]


def p_operando_simples_neg(p):
    "operando_simples : NEG valor"
    p[0] = Node("negativo", [p[2]], value="_NEG_")


def p_valor_id(p):
    "valor : ID"
    p[0] = Node("id", value=p[1])


def p_valor_numero(p):
    "valor : NUMBER"
    p[0] = Node("numero", value=p[1])


def p_valor_zero(p):
    "valor : Z"
    p[0] = Node("zero", value="_Z_")


# ================================================================ chamada de função

def p_chamada(p):
    "chamada : FUNCID LPAREN argumentos RPAREN"
    p[0] = Node("chamada", p[3], value=p[1], lineno=p.lineno(1))


def p_argumentos(p):
    """argumentos : lista_argumentos
                  | """
    p[0] = p[1] if len(p) > 1 else []


def p_lista_argumentos_um(p):
    "lista_argumentos : valor"
    p[0] = [p[1]]


def p_lista_argumentos_varios(p):
    "lista_argumentos : lista_argumentos COMMA valor"
    p[0] = p[1] + [p[3]]


# ================================================================ erros

def _expected_tokens():
    state = getattr(_parser, "state", None)
    if state is None:
        return []
    actions = _parser.action.get(state, {})
    names = [t for t in actions if t != "error"]
    return sorted(TOKEN_DESCRIPTIONS.get(t, t) for t in names)


def p_error(tok):
    expected = _expected_tokens()
    hint = ""
    if expected and len(expected) <= 6:
        hint = f"; esperado: {', '.join(expected)}"

    if tok is None:
        syntax_errors.append((None, f"fim de arquivo inesperado (faltou 'fim.'?){hint}"))
        return

    found = TOKEN_DESCRIPTIONS.get(tok.type, tok.type)
    syntax_errors.append(
        (tok.lineno, f"token inesperado {found} = {tok.value!r}{hint}")
    )


def _build_parser():
    kwargs = dict(debug=False, errorlog=yacc.NullLogger())
    try:
        return yacc.yacc(write_tables=False, **kwargs)
    except TypeError:
        return yacc.yacc(**kwargs)


_parser = _build_parser()


# ================================================================ regra de linhas
# "Sempre terminando com . e sempre um único comando por linha."
# Verificada sobre a lista de tokens (usando só o número de linha de cada
# token): a última token de cada linha tem que ser '.', e '.' tem que ser a
# última token da sua linha. Quando falta o '.', um '.' virtual é inserido
# para que o parser continue sem gerar erros em cascata na linha seguinte.

def _dot_virtual(after):
    t = lex.LexToken()
    t.type = "DOT"
    t.value = "."
    t.lineno = after.lineno
    t.lexpos = after.lexpos
    return t


def _checar_linhas(toks):
    erros = []
    saida = []
    for i, tok in enumerate(toks):
        saida.append(tok)
        prox = toks[i + 1] if i + 1 < len(toks) else None
        fim_da_linha = prox is None or prox.lineno != tok.lineno
        if tok.type == "DOT" and not fim_da_linha:
            erros.append((tok.lineno, "mais de um comando na mesma linha (algo depois do '.')"))
        elif fim_da_linha and tok.type != "DOT":
            erros.append((tok.lineno, "linha não termina com '.'"))
            saida.append(_dot_virtual(tok))
    return saida, erros


class _TokenStream:

    def __init__(self, toks):
        self._it = iter(toks)

    def token(self):
        return next(self._it, None)

    def input(self, _data):
        pass


def _ordem(err):
    lineno = err[0]
    return (lineno is None, lineno or 0)


def parse(token_list):
    global syntax_errors
    syntax_errors = []
    toks, erros_linha = _checar_linhas(list(token_list))
    tree = _parser.parse(lexer=_TokenStream(toks))
    erros = sorted(erros_linha + syntax_errors, key=_ordem)
    if erros:
        tree = None
    return tree, erros

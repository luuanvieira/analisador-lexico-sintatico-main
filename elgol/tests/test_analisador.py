from pathlib import Path

import pytest

from analyzer import analyze

TESTS = Path(__file__).parent
EXEMPLOS = TESTS / "exemplos"
CORRETOS = sorted((EXEMPLOS / "corretos").glob("*.elgol")) + [TESTS / "correto.elgol"]
INCORRETOS = sorted((EXEMPLOS / "incorretos").glob("*.elgol"))

# arquivo -> linhas em que DEVE haver erro sintático (None = fim do arquivo).
# O analisador pode relatar erros extras causados pela recuperação; o teste
# exige que pelo menos estas linhas apareçam e que a primeira seja a esperada.
ERROS_SINTATICOS_ESPERADOS = {
    "01_sem_ponto.elgol": [3],
    "02_sem_fim.elgol": [None],
    "03_sem_entao.elgol": [4],
    "04_operador_faltando.elgol": [3],
    "05_condicao_sem_relacional.elgol": [3],
    "06_atribuicao_invalida.elgol": [3],
    "07_parenteses.elgol": [3],
    "08_sem_inicio.elgol": [2],
    "09_senao_sem_se.elgol": [4],
    "10_varios_erros.elgol": [3, 5, 7],
    "11_lexico_e_sintatico.elgol": [3, 4],
    "12_sem_senao.elgol": [8],
    "13_enquanto_com_aritmetica.elgol": [3],
    "14_enquanto_tres_operandos.elgol": [3],
    "15_enquanto_com_funcao.elgol": [3],
    "16_elgio_com_funcao.elgol": [4],
    "17_funcao_como_parametro.elgol": [3],
    "18_funcao_como_alvo.elgol": [3],
    "19_sem_ponto_no_inicio.elgol": [2],
    "20_dois_comandos_na_linha.elgol": [3],
    "21_atribuicao_logica.elgol": [3],
    "22_para_sem_limite.elgol": [3],
}

# Exemplos da "Definição do Projeto — Parte 2" (pasta exemplos/professor)
PROFESSOR = {
    # arquivo: (linhas com erro léxico, linhas com erro sintático)
    "exemplo1.elgol": ([], []),
    "exemplo2.elgol": ([2, 4, 5, 6], [2, 4, 5, 6]),
    "exemplo3.elgol": ([], [2, 3, 6, 7, 11, 21, 25]),
    "exemplo4.elgol": ([20], [17, 20]),
    "exemplo5.elgol": ([18, 21], [5, 10, 18, 22, 27]),
}


def run(src):
    return analyze(src)


def linhas(errors):
    return [lineno for lineno, _ in errors]


# ---------------------------------------------------------------- arquivos de exemplo

@pytest.mark.parametrize("arquivo", CORRETOS, ids=lambda p: p.name)
def test_exemplos_corretos_sao_aceitos(arquivo):
    result = run(arquivo.read_text(encoding="utf-8"))
    assert result.lexical_errors == []
    assert result.syntax_errors == []
    assert result.tree is not None and result.tree.kind == "programa"


@pytest.mark.parametrize("arquivo", INCORRETOS, ids=lambda p: p.name)
def test_exemplos_incorretos_sao_rejeitados(arquivo):
    result = run(arquivo.read_text(encoding="utf-8"))
    assert not result.ok
    esperadas = ERROS_SINTATICOS_ESPERADOS[arquivo.name]
    encontradas = linhas(result.syntax_errors)
    assert encontradas[0] == esperadas[0], result.syntax_errors
    assert set(esperadas) <= set(encontradas), result.syntax_errors


def test_todos_os_incorretos_tem_expectativa():
    assert {p.name for p in INCORRETOS} == set(ERROS_SINTATICOS_ESPERADOS)


@pytest.mark.parametrize("arquivo", sorted(PROFESSOR), ids=str)
def test_exemplos_do_professor(arquivo):
    result = run((EXEMPLOS / "professor" / arquivo).read_text(encoding="utf-8"))
    lexicas, sintaticas = PROFESSOR[arquivo]
    if not lexicas and not sintaticas:
        assert result.ok, (result.lexical_errors, result.syntax_errors)
        return
    assert not result.ok
    assert set(lexicas) <= set(linhas(result.lexical_errors)), result.lexical_errors
    assert set(sintaticas) <= set(linhas(result.syntax_errors)), result.syntax_errors


def test_exemplo_lexico_da_parte1_continua_detectando_erros():
    result = run((TESTS / "incorreto.elgol").read_text(encoding="utf-8"))
    assert len(result.lexical_errors) == 9


# ---------------------------------------------------------------- léxico

@pytest.mark.parametrize("palavra", ["lixo", "vezes", "Variável", "Faz2", "_Teste", "_z_", "Xyz"])
def test_palavras_invalidas_sao_erro_lexico(palavra):
    result = run(f"inicio.\n    {palavra} = 1.\nfim.\n")
    assert linhas(result.lexical_errors) == [2]


@pytest.mark.parametrize("texto", ["0", ";", ">", "<", "$Fazalgo2", "034"])
def test_simbolos_invalidos_sao_erro_lexico(texto):
    result = run(f"inicio.\n    Valor = 5 {texto}\nfim.\n")
    assert 2 in linhas(result.lexical_errors)


# ---------------------------------------------------------------- estrutura da árvore

def programa(*comandos):
    return "inicio.\n" + "\n".join(comandos) + "\nfim.\n"


def comandos_principais(result):
    return result.tree.children[-1].children


def expr_da_atribuicao(src_expr):
    result = run(programa(f"Valor = {src_expr}."))
    assert result.ok, result.syntax_errors
    return comandos_principais(result)[0].children[1]


def test_sem_precedencia_avalia_da_esquerda_para_a_direita():
    # Bare + Breca x 45  ->  (Bare + Breca) x 45
    e = expr_da_atribuicao("Bare + Breca x 45")
    assert e.value == "x"
    assert e.children[0].value == "+"
    assert e.children[1].value == 45


def test_exp_tambem_associa_a_esquerda():
    e = expr_da_atribuicao("2 EXP 3 EXP 2")
    assert e.value == "EXP"
    assert e.children[0].value == "EXP"


def test_neg_como_operando():
    e = expr_da_atribuicao("_NEG_ 5 + Lixo")
    assert e.value == "+"
    assert e.children[0].kind == "negativo"


def test_chamada_de_funcao_como_operando():
    e = expr_da_atribuicao("45 x $Soma(Lixo, 30, _Z_)")
    assert e.children[1].kind == "chamada"
    assert e.children[1].value == "$Soma"
    assert len(e.children[1].children) == 3


def test_se_tem_entao_e_senao():
    result = run(programa("se Base maior 1.", "entao.", "inicio.", "Base = 1.", "fim.",
                          "senao.", "inicio.", "fim."))
    assert result.ok, result.syntax_errors
    se = comandos_principais(result)[0]
    assert [c.kind for c in se.children] == ["condicao", "entao", "senao"]
    assert se.children[0].value == "maior"
    assert se.children[2].children == []  # senao vazio


@pytest.mark.parametrize("op", ["maior", "menor", "igual", "diferente", "migual", "MIgual", "Migual"])
def test_todos_os_relacionais(op):
    result = run(programa(f"enquanto Base {op} 3.", "inicio.", "fim."))
    assert result.ok, result.syntax_errors
    assert comandos_principais(result)[0].children[0].value == op


@pytest.mark.parametrize("limite", ["100", "Limite", "_Z_"])
def test_para_com_limite(limite):
    result = run(programa(f"para Contar {limite}.", "inicio.", "fim."))
    assert result.ok, result.syntax_errors


def test_funcao_com_elgio():
    src = ("DECIMAL $Soma (DECIMAL Numm, DECIMAL Dois) .\n"
           "inicio .\n    elgio = Numm + Dois .\nfim.\n" + programa())
    result = run(src)
    assert result.ok, result.syntax_errors
    funcao = result.tree.children[0]
    assert funcao.kind == "funcao" and funcao.value == "$Soma"


# ---------------------------------------------------------------- erros pontuais

@pytest.mark.parametrize(
    "linhas_cmd",
    [
        ["Valor = ."],                              # expressão vazia
        ["Valor = 1 + ."],                          # operando faltando
        ["Valor 1."],                               # falta '='
        ["Valor = 1"],                              # falta '.'
        ["Valor = (1 + 2)."],                       # parênteses fora de função
        ["Valor = $Somar(1,)."],                    # argumento vazio
        ["Valor = $Somar(1 + 2)."],                 # expressão como argumento
        ["DECIMAL 10."],                            # declaração sem identificador
        ["DECIMAL Variavel, Lixo."],                # vírgula na declaração
        ["elgio = 1 + $Soma(1, 2)."],               # elgio com função
        ["enquanto Teste > 30.", "inicio.", "fim."],  # '>' não existe
        ["enquanto Teste maior 30", "inicio.", "fim."],  # falta '.'
        ["enquanto Teste maior 30.", "entao.", "inicio.", "fim."],  # entao no enquanto
        ["se Teste maior 30.", "inicio.", "fim.", "senao.", "inicio.", "fim."],  # falta entao
        ["para 10 Contar.", "inicio.", "fim."],     # contador tem que ser id
        ["fim."],                                   # 'fim' sobrando
    ],
)
def test_comandos_invalidos(linhas_cmd):
    result = run(programa(*linhas_cmd))
    assert not result.ok, f"deveria falhar: {linhas_cmd!r}"


def test_programa_vazio_eh_invalido():
    result = run("")
    assert linhas(result.syntax_errors) == [None]


def test_recuperacao_continua_apos_erro():
    result = run(programa("Valor = 1 +.", "Base = 2.", "Novo = x.", "Pronto = 3."))
    assert linhas(result.syntax_errors) == [2, 4]


def test_analises_consecutivas_sao_independentes():
    assert not run(programa("Valor = .")).ok
    assert run(programa("Valor = 1.")).ok

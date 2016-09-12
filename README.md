# extrator_banco_brasil
## EN_US
Extract information from text statements issued from a Brazilian bank named [Banco do Brasil](http://www.bb.com.br). If you don't have an acount at [Banco do Brasil](http://www.bb.com.br), this library has no use for you.

## PT_BR
Extrai informações dos extratos (sic) de conta corrente, BrasilPrev e fundos de investimento do [Banco do Brasil](http://www.bb.com.br). Se você não tem uma conta no [Banco do Brasil](http://www.bb.com.br), essa biblioteca não tem nenhuma utilidade para você.

No momento, estão implementados métodos para extrair informações de conta corrente, fundos de investimento e plano de previdência Brasilprev. Os dois primeiros métodos possuem teste, o último, ainda não.

Esta biblioteca está implementada em [Python](http://www.python.org) versão 3.5.

# Como usar

Baixe os extratos de conta corrente em uma pasta. Faça o mesmo para os extratos de fundos de investimento e Brasilprev. Os seguintes formatos são esperados para cada tipo:
- Conta corrente: formanto csv;
- Fundos de Investimento: formato txt;
- Brasilprev: formato txt.

Os métodos `compila_conta_corrente`, `compila_fundo_investimento` e `compila_brasilprev` retornam objetos do tipo `pandas.DataFrame`, da biblioteca [Pandas](http://pandas.pydata.org/), para análises. Por se tratar de informações sensíveis, não há como fazer um exemplo prático.

Boa sorte!
